# LifeKB iOS Data Management Guide

## 💾 Local Data Persistence with Core Data

### Core Data Stack Setup

```swift
import CoreData

class CoreDataStack {
    static let shared = CoreDataStack()
    
    private init() {}
    
    lazy var persistentContainer: NSPersistentContainer = {
        let container = NSPersistentContainer(name: "LifeKB")
        container.loadPersistentStores { _, error in
            if let error = error {
                fatalError("Core Data error: \(error)")
            }
        }
        return container
    }()
    
    var viewContext: NSManagedObjectContext {
        return persistentContainer.viewContext
    }
    
    func save() {
        let context = persistentContainer.viewContext
        
        if context.hasChanges {
            do {
                try context.save()
            } catch {
                print("Save error: \(error)")
            }
        }
    }
    
    func backgroundContext() -> NSManagedObjectContext {
        return persistentContainer.newBackgroundContext()
    }
}
```

### Core Data Model Entities

```swift
// JournalEntry+CoreDataClass.swift
import CoreData
import Foundation

@objc(JournalEntry)
public class JournalEntry: NSManagedObject {
    
    var tagsArray: [String] {
        get {
            guard let tagsString = tags else { return [] }
            return tagsString.components(separatedBy: ",").filter { !$0.isEmpty }
        }
        set {
            tags = newValue.joined(separator: ",")
        }
    }
    
    var isEmbedded: Bool {
        return embeddingStatus == "completed"
    }
    
    var needsSync: Bool {
        return lastSyncDate == nil || (updatedAt ?? Date()) > (lastSyncDate ?? Date.distantPast)
    }
}

// JournalEntry+CoreDataProperties.swift
extension JournalEntry {
    
    @NSManaged public var id: String
    @NSManaged public var text: String
    @NSManaged public var tags: String?
    @NSManaged public var category: String?
    @NSManaged public var mood: Int16
    @NSManaged public var createdAt: Date
    @NSManaged public var updatedAt: Date?
    @NSManaged public var embeddingStatus: String?
    @NSManaged public var lastSyncDate: Date?
    @NSManaged public var isLocalOnly: Bool
}
```

## 🔄 Data Synchronization Manager

```swift
import Foundation
import CoreData

class DataSyncManager {
    static let shared = DataSyncManager()
    private let apiManager = LifeKBAPIManager.shared
    private let coreDataStack = CoreDataStack.shared
    
    private init() {}
    
    // MARK: - Sync Operations
    
    func performFullSync() async throws {
        try await downloadEntriesFromServer()
        try await uploadLocalChanges()
        try await downloadEmbeddingUpdates()
    }
    
    private func downloadEntriesFromServer() async throws {
        let serverEntries = try await apiManager.getAllEntries()
        
        let context = coreDataStack.backgroundContext()
        
        await context.perform {
            for serverEntry in serverEntries {
                let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
                fetchRequest.predicate = NSPredicate(format: "id == %@", serverEntry.id)
                
                do {
                    let existingEntries = try context.fetch(fetchRequest)
                    
                    if let existingEntry = existingEntries.first {
                        // Update existing entry
                        self.updateLocalEntry(existingEntry, with: serverEntry, in: context)
                    } else {
                        // Create new entry
                        self.createLocalEntry(from: serverEntry, in: context)
                    }
                } catch {
                    print("Fetch error: \(error)")
                }
            }
            
            try? context.save()
        }
    }
    
    private func uploadLocalChanges() async throws {
        let context = coreDataStack.backgroundContext()
        
        await context.perform {
            let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
            fetchRequest.predicate = NSPredicate(format: "needsSync == true OR isLocalOnly == true")
            
            do {
                let entriesToSync = try context.fetch(fetchRequest)
                
                for entry in entriesToSync {
                    Task {
                        do {
                            if entry.isLocalOnly {
                                // Create new entry on server
                                let createRequest = CreateEntryRequest(
                                    text: entry.text,
                                    tags: entry.tagsArray.isEmpty ? nil : entry.tagsArray,
                                    category: entry.category,
                                    mood: entry.mood > 0 ? Int(entry.mood) : nil
                                )
                                
                                let serverEntry = try await self.apiManager.createEntry(createRequest)
                                
                                // Update local entry with server ID
                                await context.perform {
                                    entry.id = serverEntry.id
                                    entry.isLocalOnly = false
                                    entry.lastSyncDate = Date()
                                    try? context.save()
                                }
                            } else {
                                // Update existing entry on server
                                let updateRequest = UpdateEntryRequest(
                                    text: entry.text,
                                    tags: entry.tagsArray.isEmpty ? nil : entry.tagsArray,
                                    category: entry.category,
                                    mood: entry.mood > 0 ? Int(entry.mood) : nil
                                )
                                
                                _ = try await self.apiManager.updateEntry(id: entry.id, request: updateRequest)
                                
                                await context.perform {
                                    entry.lastSyncDate = Date()
                                    try? context.save()
                                }
                            }
                        } catch {
                            print("Sync error for entry \(entry.id): \(error)")
                        }
                    }
                }
            } catch {
                print("Fetch error: \(error)")
            }
        }
    }
    
    // MARK: - Helper Methods
    
    private func updateLocalEntry(_ localEntry: JournalEntry, with serverEntry: ServerJournalEntry, in context: NSManagedObjectContext) {
        localEntry.text = serverEntry.text
        localEntry.tagsArray = serverEntry.tags ?? []
        localEntry.category = serverEntry.category
        localEntry.mood = Int16(serverEntry.mood ?? 0)
        localEntry.embeddingStatus = serverEntry.embeddingStatus
        localEntry.lastSyncDate = Date()
        
        if let updatedAtString = serverEntry.updatedAt {
            localEntry.updatedAt = ISO8601DateFormatter().date(from: updatedAtString)
        }
    }
    
    private func createLocalEntry(from serverEntry: ServerJournalEntry, in context: NSManagedObjectContext) {
        let localEntry = JournalEntry(context: context)
        localEntry.id = serverEntry.id
        localEntry.text = serverEntry.text
        localEntry.tagsArray = serverEntry.tags ?? []
        localEntry.category = serverEntry.category
        localEntry.mood = Int16(serverEntry.mood ?? 0)
        localEntry.embeddingStatus = serverEntry.embeddingStatus
        localEntry.isLocalOnly = false
        localEntry.lastSyncDate = Date()
        
        if let createdAtString = serverEntry.createdAt {
            localEntry.createdAt = ISO8601DateFormatter().date(from: createdAtString) ?? Date()
        }
        
        if let updatedAtString = serverEntry.updatedAt {
            localEntry.updatedAt = ISO8601DateFormatter().date(from: updatedAtString)
        }
    }
}

// Server model for sync
struct ServerJournalEntry: Codable {
    let id: String
    let text: String
    let tags: [String]?
    let category: String?
    let mood: Int?
    let createdAt: String
    let updatedAt: String?
    let embeddingStatus: String?
    
    enum CodingKeys: String, CodingKey {
        case id, text, tags, category, mood
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case embeddingStatus = "embedding_status"
    }
}
```

## 📱 Offline-First Architecture

### Offline Data Manager

```swift
class OfflineDataManager {
    static let shared = OfflineDataManager()
    private let coreDataStack = CoreDataStack.shared
    
    private init() {}
    
    // MARK: - Offline Entry Management
    
    func createOfflineEntry(text: String, tags: [String]? = nil, category: String? = nil, mood: Int? = nil) -> JournalEntry {
        let context = coreDataStack.viewContext
        let entry = JournalEntry(context: context)
        
        entry.id = UUID().uuidString // Temporary local ID
        entry.text = text
        entry.tagsArray = tags ?? []
        entry.category = category
        entry.mood = Int16(mood ?? 0)
        entry.createdAt = Date()
        entry.isLocalOnly = true
        
        coreDataStack.save()
        
        // Schedule sync when online
        NotificationCenter.default.post(name: .dataRequiresSync, object: nil)
        
        return entry
    }
    
    func updateOfflineEntry(_ entry: JournalEntry, text: String, tags: [String]? = nil, category: String? = nil, mood: Int? = nil) {
        entry.text = text
        entry.tagsArray = tags ?? []
        entry.category = category
        entry.mood = Int16(mood ?? 0)
        entry.updatedAt = Date()
        
        coreDataStack.save()
        
        // Schedule sync when online
        NotificationCenter.default.post(name: .dataRequiresSync, object: nil)
    }
    
    func deleteOfflineEntry(_ entry: JournalEntry) {
        let context = coreDataStack.viewContext
        context.delete(entry)
        coreDataStack.save()
        
        // If it was synced, mark for server deletion
        if !entry.isLocalOnly {
            // Store deletion marker or handle via sync
        }
    }
    
    // MARK: - Search Offline
    
    func searchOfflineEntries(query: String) -> [JournalEntry] {
        let context = coreDataStack.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        
        fetchRequest.predicate = NSPredicate(format: "text CONTAINS[cd] %@", query)
        fetchRequest.sortDescriptors = [NSSortDescriptor(key: "createdAt", ascending: false)]
        
        do {
            return try context.fetch(fetchRequest)
        } catch {
            print("Offline search error: \(error)")
            return []
        }
    }
    
    func getAllOfflineEntries() -> [JournalEntry] {
        let context = coreDataStack.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        fetchRequest.sortDescriptors = [NSSortDescriptor(key: "createdAt", ascending: false)]
        
        do {
            return try context.fetch(fetchRequest)
        } catch {
            print("Fetch error: \(error)")
            return []
        }
    }
    
    // MARK: - Sync Status
    
    func getUnsyncedEntriesCount() -> Int {
        let context = coreDataStack.viewContext
        let fetchRequest: NSFetchRequest<JournalEntry> = JournalEntry.fetchRequest()
        fetchRequest.predicate = NSPredicate(format: "needsSync == true OR isLocalOnly == true")
        
        do {
            return try context.count(for: fetchRequest)
        } catch {
            return 0
        }
    }
}

extension Notification.Name {
    static let dataRequiresSync = Notification.Name("dataRequiresSync")
}
```

## 🌐 Network Reachability

```swift
import Network

class NetworkMonitor: ObservableObject {
    static let shared = NetworkMonitor()
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")
    
    @Published var isConnected = false
    @Published var connectionType = ConnectionType.unknown
    
    enum ConnectionType {
        case wifi
        case cellular
        case ethernet
        case unknown
    }
    
    private init() {
        startMonitoring()
    }
    
    func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
                self?.updateConnectionType(path)
            }
            
            // Trigger sync when connection is restored
            if path.status == .satisfied {
                NotificationCenter.default.post(name: .networkConnected, object: nil)
            }
        }
        monitor.start(queue: queue)
    }
    
    private func updateConnectionType(_ path: NWPath) {
        if path.usesInterfaceType(.wifi) {
            connectionType = .wifi
        } else if path.usesInterfaceType(.cellular) {
            connectionType = .cellular
        } else if path.usesInterfaceType(.wiredEthernet) {
            connectionType = .ethernet
        } else {
            connectionType = .unknown
        }
    }
    
    deinit {
        monitor.cancel()
    }
}

extension Notification.Name {
    static let networkConnected = Notification.Name("networkConnected")
}
```

## 📊 Smart Caching Strategy

```swift
class CacheManager {
    static let shared = CacheManager()
    private let cache = NSCache<NSString, NSData>()
    private let fileManager = FileManager.default
    
    private init() {
        setupCache()
    }
    
    private func setupCache() {
        cache.countLimit = 100 // Max 100 cached responses
        cache.totalCostLimit = 50 * 1024 * 1024 // 50MB max
    }
    
    // MARK: - API Response Caching
    
    func cacheAPIResponse<T: Codable>(_ response: T, for key: String, ttl: TimeInterval = 300) {
        do {
            let data = try JSONEncoder().encode(response)
            let cacheItem = CacheItem(data: data, expiry: Date().addingTimeInterval(ttl))
            let itemData = try JSONEncoder().encode(cacheItem)
            
            cache.setObject(itemData as NSData, forKey: key as NSString)
        } catch {
            print("Cache save error: \(error)")
        }
    }
    
    func getCachedResponse<T: Codable>(for key: String, type: T.Type) -> T? {
        guard let data = cache.object(forKey: key as NSString) as Data? else {
            return nil
        }
        
        do {
            let cacheItem = try JSONDecoder().decode(CacheItem.self, from: data)
            
            if cacheItem.expiry < Date() {
                cache.removeObject(forKey: key as NSString)
                return nil
            }
            
            return try JSONDecoder().decode(type, from: cacheItem.data)
        } catch {
            cache.removeObject(forKey: key as NSString)
            return nil
        }
    }
    
    // MARK: - Image Caching (for future features)
    
    func cacheImage(_ imageData: Data, for key: String) {
        cache.setObject(imageData as NSData, forKey: key as NSString)
    }
    
    func getCachedImage(for key: String) -> Data? {
        return cache.object(forKey: key as NSString) as Data?
    }
    
    func clearCache() {
        cache.removeAllObjects()
    }
}

struct CacheItem: Codable {
    let data: Data
    let expiry: Date
}
```

## 🔄 Auto-Sync Implementation

```swift
class AutoSyncManager {
    static let shared = AutoSyncManager()
    private let syncManager = DataSyncManager.shared
    private let networkMonitor = NetworkMonitor.shared
    
    private var syncTimer: Timer?
    private var backgroundTask: UIBackgroundTaskIdentifier = .invalid
    
    private init() {
        setupObservers()
    }
    
    private func setupObservers() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(networkConnected),
            name: .networkConnected,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(dataRequiresSync),
            name: .dataRequiresSync,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(appDidEnterBackground),
            name: UIApplication.didEnterBackgroundNotification,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(appWillEnterForeground),
            name: UIApplication.willEnterForegroundNotification,
            object: nil
        )
    }
    
    @objc private func networkConnected() {
        performSync()
    }
    
    @objc private func dataRequiresSync() {
        if networkMonitor.isConnected {
            performSync()
        }
    }
    
    @objc private func appDidEnterBackground() {
        startBackgroundSync()
    }
    
    @objc private func appWillEnterForeground() {
        endBackgroundTask()
        performSync()
    }
    
    private func performSync() {
        Task {
            do {
                try await syncManager.performFullSync()
                print("✅ Sync completed successfully")
            } catch {
                print("❌ Sync failed: \(error)")
                // Retry later
                scheduleRetrySync()
            }
        }
    }
    
    private func scheduleRetrySync() {
        syncTimer?.invalidate()
        syncTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: false) { _ in
            if self.networkMonitor.isConnected {
                self.performSync()
            }
        }
    }
    
    private func startBackgroundSync() {
        backgroundTask = UIApplication.shared.beginBackgroundTask { [weak self] in
            self?.endBackgroundTask()
        }
        
        // Perform quick sync in background
        Task {
            do {
                try await syncManager.performFullSync()
            } catch {
                print("Background sync failed: \(error)")
            }
            endBackgroundTask()
        }
    }
    
    private func endBackgroundTask() {
        if backgroundTask != .invalid {
            UIApplication.shared.endBackgroundTask(backgroundTask)
            backgroundTask = .invalid
        }
    }
}
``` 