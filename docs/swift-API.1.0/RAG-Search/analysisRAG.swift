let parameters = "{\n    \"query\": \"What patterns do you see in my behavior?\",\n    \"mode\": \"analysis\",\n    \"include_sources\": true,\n    \"limit\": 20\n}"
let postData = parameters.data(using: .utf8)

var request = URLRequest(url: URL(string: "https://life-kb-server.vercel.app/api/search_rag")!,timeoutInterval: Double.infinity)
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
