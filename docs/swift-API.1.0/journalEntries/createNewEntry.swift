let parameters = "{\n    \"text\": \"Today was an amazing day! I went for a long walk in the park, had coffee with a close friend, and finished reading a fascinating book about mindfulness. I'm feeling grateful for these simple pleasures in life.\",\n    \"tags\": [\"gratitude\", \"friendship\", \"mindfulness\"],\n    \"category\": \"personal\",\n    \"mood\": 8\n}"
let postData = parameters.data(using: .utf8)

var request = URLRequest(url: URL(string: "https://life-kb-server.vercel.app/api/entries")!,timeoutInterval: Double.infinity)
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
