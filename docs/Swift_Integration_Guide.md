# LifeKB API Swift Integration Guide

## 📱 iOS Development with LifeKB APIs

This guide provides Swift code examples and best practices for integrating LifeKB APIs into your iOS app.

## 🔧 Setup

### 1. API Configuration

```swift
import Foundation

struct LifeKBConfig {
    static let baseURL = "https://your-domain.vercel.app" // or "http://localhost:3000" for development
    static let timeout: TimeInterval = 30.0
}
```

### 2. Base API Manager

```swift
import Foundation

class LifeKBAPIManager {
    static let shared = LifeKBAPIManager()
    private let session: URLSession
    
    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = LifeKBConfig.timeout
        config.timeoutIntervalForResource = LifeKBConfig.timeout
        self.session = URLSession(configuration: config)
    }
    
    // Store auth token securely
    private var authToken: String? {
        get { UserDefaults.standard.string(forKey: "lifekb_auth_token") }
        set { 
            if let token = newValue {
                UserDefaults.standard.set(token, forKey: "lifekb_auth_token")
            } else {
                UserDefaults.standard.removeObject(forKey: "lifekb_auth_token")
            }
        }
    }
    
    func setAuthToken(_ token: String) {
        self.authToken = token
    }
    
    func clearAuthToken() {
        self.authToken = nil
    }
}
```

## 🔐 Authentication Models & API

### Authentication Models

```swift
// MARK: - Auth Request Models
struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct SignupRequest: Codable {
    let email: String
    let password: String
}

// MARK: - Auth Response Models
struct LoginResponse: Codable {
    let success: Bool
    let token: String
    let userId: String
    
    enum CodingKeys: String, CodingKey {
        case success, token
        case userId = "user_id"
    }
}

struct SignupResponse: Codable {
    let success: Bool
    let userId: String
    
    enum CodingKeys: String, CodingKey {
        case success
        case userId = "user_id"
    }
}

struct APIStatusResponse: Codable {
    let api: String
    let status: String
    let version: String?
}
```

### Authentication API Extension

```swift
extension LifeKBAPIManager {
    
    func login(email: String, password: String) async throws -> LoginResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let loginRequest = LoginRequest(email: email, password: password)
        request.httpBody = try JSONEncoder().encode(loginRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        // Auto-save token
        if loginResponse.success {
            setAuthToken(loginResponse.token)
        }
        
        return loginResponse
    }
    
    func signup(email: String, password: String) async throws -> SignupResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/auth/signup")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let signupRequest = SignupRequest(email: email, password: password)
        request.httpBody = try JSONEncoder().encode(signupRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(SignupResponse.self, from: data)
    }
}
```

## 📝 Journal Entries Models & API

### Journal Entry Models

```swift
// MARK: - Journal Entry Models
struct JournalEntry: Codable, Identifiable {
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

struct CreateEntryRequest: Codable {
    let text: String
    let tags: [String]?
    let category: String?
    let mood: Int?
}

struct UpdateEntryRequest: Codable {
    let text: String
    let tags: [String]?
    let category: String?
    let mood: Int?
}

struct EntriesResponse: Codable {
    let success: Bool
    let entries: [JournalEntry]
    let total: Int
}

struct SingleEntryResponse: Codable {
    let success: Bool
    let entry: JournalEntry
}

struct CreateEntryResponse: Codable {
    let success: Bool
    let entry: JournalEntry
}
```

### Journal Entries API Extension

```swift
extension LifeKBAPIManager {
    
    private func createAuthenticatedRequest(url: URL, method: String = "GET") throws -> URLRequest {
        guard let token = authToken else {
            throw APIError.noAuthToken
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        return request
    }
    
    func getAllEntries() async throws -> EntriesResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/entries")!
        let request = try createAuthenticatedRequest(url: url)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(EntriesResponse.self, from: data)
    }
    
    func getEntry(id: String) async throws -> SingleEntryResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/entries?id=\(id)")!
        let request = try createAuthenticatedRequest(url: url)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(SingleEntryResponse.self, from: data)
    }
    
    func createEntry(text: String, tags: [String]? = nil, category: String? = nil, mood: Int? = nil) async throws -> CreateEntryResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/entries")!
        var request = try createAuthenticatedRequest(url: url, method: "POST")
        
        let createRequest = CreateEntryRequest(text: text, tags: tags, category: category, mood: mood)
        request.httpBody = try JSONEncoder().encode(createRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 201 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(CreateEntryResponse.self, from: data)
    }
    
    func updateEntry(id: String, text: String, tags: [String]? = nil, category: String? = nil, mood: Int? = nil) async throws -> CreateEntryResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/entries?id=\(id)")!
        var request = try createAuthenticatedRequest(url: url, method: "PUT")
        
        let updateRequest = UpdateEntryRequest(text: text, tags: tags, category: category, mood: mood)
        request.httpBody = try JSONEncoder().encode(updateRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(CreateEntryResponse.self, from: data)
    }
    
    func deleteEntry(id: String) async throws {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/entries?id=\(id)")!
        let request = try createAuthenticatedRequest(url: url, method: "DELETE")
        
        let (_, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
    }
}
```

## 🔍 Search & RAG Models & API

### Search Models

```swift
// MARK: - Search Models
struct SearchRequest: Codable {
    let query: String
    let limit: Int?
    let similarityThreshold: Double?
    
    enum CodingKeys: String, CodingKey {
        case query, limit
        case similarityThreshold = "similarity_threshold"
    }
}

struct SearchResult: Codable {
    let id: String
    let text: String
    let createdAt: String
    let similarity: Double
    
    enum CodingKeys: String, CodingKey {
        case id, text, similarity
        case createdAt = "created_at"
    }
}

struct SearchResponse: Codable {
    let success: Bool
    let query: String
    let results: [SearchResult]
    let totalCount: Int
    let similarityThreshold: Double
    let searchTimeMs: Double
    
    enum CodingKeys: String, CodingKey {
        case success, query, results
        case totalCount = "total_count"
        case similarityThreshold = "similarity_threshold"
        case searchTimeMs = "search_time_ms"
    }
}

// MARK: - RAG Models
enum RAGMode: String, CaseIterable, Codable {
    case conversational = "conversational"
    case summary = "summary"
    case analysis = "analysis"
}

struct RAGRequest: Codable {
    let query: String
    let mode: RAGMode
    let includeSources: Bool
    let limit: Int?
    
    enum CodingKeys: String, CodingKey {
        case query, mode, limit
        case includeSources = "include_sources"
    }
}

struct RAGResponse: Codable {
    let success: Bool
    let query: String
    let aiResponse: String
    let mode: RAGMode
    let totalSources: Int
    let sources: [SearchResult]?
    let processingTimeMs: Double
    
    enum CodingKeys: String, CodingKey {
        case success, query, mode, sources
        case aiResponse = "ai_response"
        case totalSources = "total_sources"
        case processingTimeMs = "processing_time_ms"
    }
}
```

### Search & RAG API Extension

```swift
extension LifeKBAPIManager {
    
    func semanticSearch(query: String, limit: Int = 10, similarityThreshold: Double = 0.1) async throws -> SearchResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/search")!
        var request = try createAuthenticatedRequest(url: url, method: "POST")
        
        let searchRequest = SearchRequest(query: query, limit: limit, similarityThreshold: similarityThreshold)
        request.httpBody = try JSONEncoder().encode(searchRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(SearchResponse.self, from: data)
    }
    
    func ragSearch(query: String, mode: RAGMode = .conversational, includeSources: Bool = true, limit: Int = 10) async throws -> RAGResponse {
        let url = URL(string: "\(LifeKBConfig.baseURL)/api/search_rag")!
        var request = try createAuthenticatedRequest(url: url, method: "POST")
        
        let ragRequest = RAGRequest(query: query, mode: mode, includeSources: includeSources, limit: limit)
        request.httpBody = try JSONEncoder().encode(ragRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(RAGResponse.self, from: data)
    }
}
```

## ⚠️ Error Handling

### Error Types

```swift
enum APIError: Error, LocalizedError {
    case invalidURL
    case noAuthToken
    case invalidResponse
    case httpError(Int)
    case decodingError(Error)
    case networkError(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .noAuthToken:
            return "No authentication token available. Please log in."
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP Error: \(code)"
        case .decodingError(let error):
            return "Data parsing error: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}
```

## 📱 SwiftUI Usage Examples

### Authentication View

```swift
import SwiftUI

struct LoginView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 20) {
            TextField("Email", text: $email)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .autocapitalization(.none)
                .keyboardType(.emailAddress)
            
            SecureField("Password", text: $password)
                .textFieldStyle(RoundedBorderTextFieldStyle())
            
            Button("Login") {
                login()
            }
            .disabled(isLoading)
            
            if let error = errorMessage {
                Text(error)
                    .foregroundColor(.red)
                    .font(.caption)
            }
        }
        .padding()
    }
    
    private func login() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let response = try await LifeKBAPIManager.shared.login(email: email, password: password)
                if response.success {
                    // Navigate to main app
                    DispatchQueue.main.async {
                        // Handle successful login
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }
}
```

### Journal Entries List View

```swift
import SwiftUI

struct EntriesListView: View {
    @State private var entries: [JournalEntry] = []
    @State private var isLoading = false
    
    var body: some View {
        NavigationView {
            List(entries) { entry in
                VStack(alignment: .leading, spacing: 8) {
                    Text(entry.text)
                        .lineLimit(3)
                    
                    HStack {
                        if let mood = entry.mood {
                            Text("Mood: \(mood)/10")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        
                        Spacer()
                        
                        Text(formatDate(entry.createdAt))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }
            .navigationTitle("Journal Entries")
            .refreshable {
                await loadEntries()
            }
        }
        .task {
            await loadEntries()
        }
    }
    
    private func loadEntries() async {
        isLoading = true
        
        do {
            let response = try await LifeKBAPIManager.shared.getAllEntries()
            DispatchQueue.main.async {
                self.entries = response.entries
                self.isLoading = false
            }
        } catch {
            DispatchQueue.main.async {
                self.isLoading = false
                // Handle error
                print("Error loading entries: \(error)")
            }
        }
    }
    
    private func formatDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: dateString) else {
            return dateString
        }
        
        let displayFormatter = DateFormatter()
        displayFormatter.dateStyle = .medium
        displayFormatter.timeStyle = .short
        return displayFormatter.string(from: date)
    }
}
```

### RAG Search View

```swift
import SwiftUI

struct RAGSearchView: View {
    @State private var query = ""
    @State private var selectedMode: RAGMode = .conversational
    @State private var response: RAGResponse?
    @State private var isLoading = false
    
    var body: some View {
        VStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Ask about your journal:")
                    .font(.headline)
                
                TextField("How have I been feeling lately?", text: $query)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                
                Picker("Mode", selection: $selectedMode) {
                    Text("Conversational").tag(RAGMode.conversational)
                    Text("Summary").tag(RAGMode.summary)
                    Text("Analysis").tag(RAGMode.analysis)
                }
                .pickerStyle(SegmentedPickerStyle())
            }
            
            Button("Search") {
                performRAGSearch()
            }
            .disabled(query.isEmpty || isLoading)
            
            if isLoading {
                ProgressView("Analyzing your journal...")
            }
            
            if let response = response {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("AI Response:")
                            .font(.headline)
                        
                        Text(response.aiResponse)
                            .padding()
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(8)
                        
                        if let sources = response.sources, !sources.isEmpty {
                            Text("Based on \(sources.count) journal entries:")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        
                        Text("Processing time: \(String(format: "%.1f", response.processingTimeMs))ms")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            Spacer()
        }
        .padding()
    }
    
    private func performRAGSearch() {
        isLoading = true
        response = nil
        
        Task {
            do {
                let ragResponse = try await LifeKBAPIManager.shared.ragSearch(
                    query: query,
                    mode: selectedMode,
                    includeSources: true
                )
                
                DispatchQueue.main.async {
                    self.response = ragResponse
                    self.isLoading = false
                }
            } catch {
                DispatchQueue.main.async {
                    self.isLoading = false
                    // Handle error
                    print("RAG search error: \(error)")
                }
            }
        }
    }
}
```

## 🔧 Best Practices

### 1. **Secure Token Storage**
```swift
import Security

class SecureTokenStorage {
    private let service = "LifeKBApp"
    private let account = "auth_token"
    
    func save(token: String) {
        let data = Data(token.utf8)
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    func load() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        
        if status == errSecSuccess,
           let data = dataTypeRef as? Data {
            return String(data: data, encoding: .utf8)
        }
        
        return nil
    }
}
```

### 2. **Network Monitoring**
```swift
import Network

class NetworkMonitor: ObservableObject {
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")
    
    @Published var isConnected = false
    
    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
            }
        }
        monitor.start(queue: queue)
    }
}
```

### 3. **Response Caching**
```swift
extension LifeKBAPIManager {
    private func cachedResponse<T: Codable>(for key: String, type: T.Type) -> T? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
    
    private func cacheResponse<T: Codable>(_ response: T, for key: String) {
        if let data = try? JSONEncoder().encode(response) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }
}
```

## 🚀 Deployment & Testing

### Testing with Postman Collection
1. Import `LifeKB_API_Collection.postman_collection.json`
2. Import `LifeKB_Local_Environment.postman_environment.json`
3. Run login request to get auth token
4. Test all endpoints with real data

### Production Configuration
Update `LifeKBConfig.baseURL` to your production domain before release.

### Error Logging
Implement comprehensive error logging for production debugging:

```swift
func logAPIError(_ error: Error, endpoint: String) {
    print("API Error at \(endpoint): \(error)")
    // Send to your analytics service
}
```

This guide provides everything you need to integrate LifeKB APIs into your Swift iOS app! 🎯 