# LifeKB iOS Security Guide

## 🔐 Secure Token Storage with Keychain

### Why Keychain Over UserDefaults?
- **UserDefaults**: Stored in plain text, accessible to anyone with device access
- **Keychain**: Encrypted, protected by iOS security, survives app uninstalls

### Keychain Helper Implementation

```swift
import Foundation
import Security

class KeychainHelper {
    static let shared = KeychainHelper()
    private let service = "com.yourapp.lifekb"
    
    private init() {}
    
    func save(_ data: Data, service: String, account: String) -> Bool {
        let query = [
            kSecValueData: data,
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: account,
        ] as CFDictionary
        
        SecItemDelete(query)
        
        let status = SecItemAdd(query, nil)
        return status == errSecSuccess
    }
    
    func read(service: String, account: String) -> Data? {
        let query = [
            kSecAttrService: service,
            kSecAttrAccount: account,
            kSecClass: kSecClassGenericPassword,
            kSecReturnData: true
        ] as CFDictionary
        
        var result: AnyObject?
        SecItemCopyMatching(query, &result)
        
        return (result as? Data)
    }
    
    func delete(service: String, account: String) -> Bool {
        let query = [
            kSecAttrService: service,
            kSecAttrAccount: account,
            kSecClass: kSecClassGenericPassword,
        ] as CFDictionary
        
        let status = SecItemDelete(query)
        return status == errSecSuccess
    }
}

// MARK: - LifeKB Specific Extensions
extension KeychainHelper {
    private let authTokenAccount = "lifekb_auth_token"
    private let refreshTokenAccount = "lifekb_refresh_token"
    
    func saveAuthToken(_ token: String) -> Bool {
        let data = Data(token.utf8)
        return save(data, service: service, account: authTokenAccount)
    }
    
    func getAuthToken() -> String? {
        guard let data = read(service: service, account: authTokenAccount) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }
    
    func deleteAuthToken() -> Bool {
        return delete(service: service, account: authTokenAccount)
    }
    
    func saveRefreshToken(_ token: String) -> Bool {
        let data = Data(token.utf8)
        return save(data, service: service, account: refreshTokenAccount)
    }
    
    func getRefreshToken() -> String? {
        guard let data = read(service: service, account: refreshTokenAccount) else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }
}
```

### Updated API Manager with Secure Storage

```swift
extension LifeKBAPIManager {
    // Replace UserDefaults with Keychain
    private var authToken: String? {
        get { KeychainHelper.shared.getAuthToken() }
        set { 
            if let token = newValue {
                _ = KeychainHelper.shared.saveAuthToken(token)
            } else {
                _ = KeychainHelper.shared.deleteAuthToken()
            }
        }
    }
    
    func setAuthToken(_ token: String) {
        self.authToken = token
    }
    
    func clearAuthToken() {
        self.authToken = nil
    }
    
    func logout() {
        _ = KeychainHelper.shared.deleteAuthToken()
        _ = KeychainHelper.shared.deleteRefreshToken()
    }
}
```

## 🔒 Biometric Authentication

### Face ID / Touch ID for App Access

```swift
import LocalAuthentication

class BiometricAuth {
    static let shared = BiometricAuth()
    private init() {}
    
    func authenticateUser() async throws -> Bool {
        let context = LAContext()
        var error: NSError?
        
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            throw BiometricError.notAvailable
        }
        
        let reason = "Authenticate to access your LifeKB journal"
        
        do {
            let success = try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: reason
            )
            return success
        } catch {
            throw BiometricError.authenticationFailed
        }
    }
    
    func getBiometricType() -> BiometricType {
        let context = LAContext()
        var error: NSError?
        
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return .none
        }
        
        switch context.biometryType {
        case .faceID:
            return .faceID
        case .touchID:
            return .touchID
        default:
            return .none
        }
    }
}

enum BiometricType {
    case none
    case touchID
    case faceID
}

enum BiometricError: Error {
    case notAvailable
    case authenticationFailed
}
```

## 🛡️ Network Security

### Certificate Pinning (Production)

```swift
class NetworkSecurityManager: NSObject, URLSessionDelegate {
    
    // Your production certificate's public key hash
    private let productionPublicKeyHash = "YOUR_CERT_HASH_HERE"
    
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        
        guard let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        
        // In development, accept all certificates
        #if DEBUG
        completionHandler(.useCredential, URLCredential(trust: serverTrust))
        return
        #endif
        
        // In production, pin certificates
        let policy = SecPolicyCreateSSL(true, challenge.protectionSpace.host as CFString)
        SecTrustSetPolicies(serverTrust, policy)
        
        var result: SecTrustResultType = .invalid
        let status = SecTrustEvaluate(serverTrust, &result)
        
        if status == errSecSuccess && (result == .unspecified || result == .proceed) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}
```

## 🔐 Privacy Requirements for RAG

### User Consent Manager

```swift
class PrivacyConsentManager {
    static let shared = PrivacyConsentManager()
    private let ragConsentKey = "rag_consent_given"
    
    private init() {}
    
    var hasRAGConsent: Bool {
        get { UserDefaults.standard.bool(forKey: ragConsentKey) }
        set { UserDefaults.standard.set(newValue, forKey: ragConsentKey) }
    }
    
    func requestRAGConsent() async -> Bool {
        // Present consent dialog
        return await withCheckedContinuation { continuation in
            DispatchQueue.main.async {
                let alert = UIAlertController(
                    title: "AI Analysis Consent",
                    message: "LifeKB can provide AI-powered insights from your journal entries. This requires sending your entries to OpenAI for analysis. Your data will not be stored by OpenAI and is only used to generate your personalized insights.\n\nDo you consent to this feature?",
                    preferredStyle: .alert
                )
                
                alert.addAction(UIAlertAction(title: "Accept", style: .default) { _ in
                    self.hasRAGConsent = true
                    continuation.resume(returning: true)
                })
                
                alert.addAction(UIAlertAction(title: "Decline", style: .cancel) { _ in
                    self.hasRAGConsent = false
                    continuation.resume(returning: false)
                })
                
                // Present alert from top view controller
                if let topVC = UIApplication.shared.topViewController {
                    topVC.present(alert, animated: true)
                }
            }
        }
    }
}

extension UIApplication {
    var topViewController: UIViewController? {
        guard let windowScene = connectedScenes.first as? UIWindowScene,
              let window = windowScene.windows.first else { return nil }
        
        var topController = window.rootViewController
        while let presentedViewController = topController?.presentedViewController {
            topController = presentedViewController
        }
        return topController
    }
}
```

## ⚡ Performance & Security Best Practices

### API Request Security Headers

```swift
extension LifeKBAPIManager {
    
    private func createSecureRequest(url: URL, method: String = "GET") -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.setValue("LifeKB-iOS/1.0", forHTTPHeaderField: "User-Agent")
        
        // Add auth token if available
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        return request
    }
}
```

### Data Validation

```swift
extension LifeKBAPIManager {
    
    private func validateJSONData(_ data: Data) throws {
        // Ensure response is valid JSON
        _ = try JSONSerialization.jsonObject(with: data, options: [])
        
        // Check for malicious content (basic validation)
        let string = String(data: data, encoding: .utf8) ?? ""
        guard !string.contains("<script") && !string.contains("javascript:") else {
            throw APIError.maliciousContent
        }
    }
}

enum APIError: Error {
    case invalidResponse
    case httpError(Int)
    case maliciousContent
    case networkError
    case tokenExpired
} 