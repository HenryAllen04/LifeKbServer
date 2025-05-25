var request = URLRequest(url: URL(string: "http://localhost:3000/api/entries?id={{entryId}}")!,timeoutInterval: Double.infinity)
request.addValue("Bearer {{authToken}}", forHTTPHeaderField: "Authorization")

request.httpMethod = "GET"

let task = URLSession.shared.dataTask(with: request) { data, response, error in 
  guard let data = data else {
    print(String(describing: error))
    return
  }
  print(String(data: data, encoding: .utf8)!)
}

task.resume()
