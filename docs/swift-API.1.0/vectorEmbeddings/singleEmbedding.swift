let parameters = "{\n    \"action\": \"generate\",\n    \"entry_id\": \"\"\n}"
let postData = parameters.data(using: .utf8)

var request = URLRequest(url: URL(string: "https://life-kb-server.vercel.app/api/embeddings")!,timeoutInterval: Double.infinity)
request.addValue("Bearer ", forHTTPHeaderField: "Authorization")
request.addValue("application/json", forHTTPHeaderField: "Content-Type")

request.httpMethod = "POST"
request.httpBody = postData

let task = URLSession.shared.dataTask(with: request) { data, response, error in 
  guard let data = data else {
    print(String(describing: error))
    return
  }
  print(String(data: data, encoding: .utf8)!)
}

task.resume()
