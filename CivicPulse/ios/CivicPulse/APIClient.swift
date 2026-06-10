import Foundation

// MARK: - Errors

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case server(statusCode: Int, message: String?)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid request URL."
        case .invalidResponse:
            return "The server returned an unexpected response."
        case .server(let statusCode, let message):
            if let message, !message.isEmpty {
                return "Server error (\(statusCode)): \(message)"
            }
            return "Server error (\(statusCode))."
        }
    }
}

// MARK: - Client

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    // MARK: Coding

    /// ISO 8601 decoder tolerant of fractional seconds and missing time zones
    /// (e.g. FastAPI emits "2026-06-10T12:34:56.789012" with no offset).
    static let decoder: JSONDecoder = {
        let withFractional = ISO8601DateFormatter()
        withFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]

        let naiveFractional = DateFormatter()
        naiveFractional.locale = Locale(identifier: "en_US_POSIX")
        naiveFractional.timeZone = TimeZone(secondsFromGMT: 0)
        naiveFractional.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"

        let naive = DateFormatter()
        naive.locale = Locale(identifier: "en_US_POSIX")
        naive.timeZone = TimeZone(secondsFromGMT: 0)
        naive.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)
            if let date = withFractional.date(from: string)
                ?? plain.date(from: string)
                ?? naiveFractional.date(from: string)
                ?? naive.date(from: string) {
                return date
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unrecognized ISO 8601 date: \(string)"
            )
        }
        return decoder
    }()

    static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    // MARK: Users

    func register(deviceID: String, zipCode: String, name: String?, email: String?, phone: String?) async throws -> User {
        struct Payload: Encodable {
            let deviceID: String
            let zipCode: String
            let name: String?
            let email: String?
            let phone: String?

            enum CodingKeys: String, CodingKey {
                case deviceID = "device_id"
                case zipCode = "zip_code"
                case name, email, phone
            }
        }
        return try await request(
            method: "POST",
            path: "api/users/register",
            body: Payload(deviceID: deviceID, zipCode: zipCode, name: name, email: email, phone: phone)
        )
    }

    func updateUser(id: Int, zipCode: String?, name: String?, email: String?, phone: String?) async throws -> User {
        struct Payload: Encodable {
            let zipCode: String?
            let name: String?
            let email: String?
            let phone: String?

            enum CodingKeys: String, CodingKey {
                case zipCode = "zip_code"
                case name, email, phone
            }
        }
        return try await request(
            method: "PATCH",
            path: "api/users/\(id)",
            body: Payload(zipCode: zipCode, name: name, email: email, phone: phone)
        )
    }

    func sendDeviceToken(userID: Int, token: String) async throws {
        struct Payload: Encodable { let token: String }
        let _: OKResponse = try await request(
            method: "POST",
            path: "api/users/\(userID)/device-token",
            body: Payload(token: token)
        )
    }

    // MARK: Representatives

    func lookupReps(zip: String) async throws -> RepLookupResponse {
        try await request(
            method: "GET",
            path: "api/reps/lookup",
            queryItems: [URLQueryItem(name: "zip", value: zip)]
        )
    }

    // MARK: Articles

    func articles(limit: Int = 50, offset: Int = 0) async throws -> [Article] {
        try await request(
            method: "GET",
            path: "api/articles",
            queryItems: [
                URLQueryItem(name: "limit", value: String(limit)),
                URLQueryItem(name: "offset", value: String(offset)),
            ]
        )
    }

    func article(id: Int) async throws -> Article {
        try await request(method: "GET", path: "api/articles/\(id)")
    }

    func postEvent(articleID: Int, userID: Int, event: EngagementEvent) async throws {
        struct Payload: Encodable {
            let userID: Int
            let event: String

            enum CodingKeys: String, CodingKey {
                case userID = "user_id"
                case event
            }
        }
        let _: OKResponse = try await request(
            method: "POST",
            path: "api/articles/\(articleID)/events",
            body: Payload(userID: userID, event: event.rawValue)
        )
    }

    // MARK: Messages

    func draftMessage(userID: Int, articleID: Int, repBioguideID: String, thoughts: String) async throws -> MessageDraft {
        struct Payload: Encodable {
            let userID: Int
            let articleID: Int
            let repBioguideID: String
            let thoughts: String

            enum CodingKeys: String, CodingKey {
                case userID = "user_id"
                case articleID = "article_id"
                case repBioguideID = "rep_bioguide_id"
                case thoughts
            }
        }
        return try await request(
            method: "POST",
            path: "api/messages/draft",
            body: Payload(userID: userID, articleID: articleID, repBioguideID: repBioguideID, thoughts: thoughts)
        )
    }

    func createMessage(
        userID: Int,
        articleID: Int?,
        repBioguideID: String,
        subject: String,
        body: String,
        deliveryMethod: DeliveryMethod
    ) async throws -> CongressMessage {
        struct Payload: Encodable {
            let userID: Int
            let articleID: Int?
            let repBioguideID: String
            let subject: String
            let body: String
            let deliveryMethod: String

            enum CodingKeys: String, CodingKey {
                case userID = "user_id"
                case articleID = "article_id"
                case repBioguideID = "rep_bioguide_id"
                case subject
                case body
                case deliveryMethod = "delivery_method"
            }
        }
        return try await request(
            method: "POST",
            path: "api/messages",
            body: Payload(
                userID: userID,
                articleID: articleID,
                repBioguideID: repBioguideID,
                subject: subject,
                body: body,
                deliveryMethod: deliveryMethod.rawValue
            )
        )
    }

    func messages(userID: Int) async throws -> [CongressMessage] {
        try await request(
            method: "GET",
            path: "api/messages",
            queryItems: [URLQueryItem(name: "user_id", value: String(userID))]
        )
    }

    // MARK: Actions

    func candidates() async throws -> [Candidate] {
        try await request(method: "GET", path: "api/candidates")
    }

    func voterRegistration(state: String) async throws -> VoterRegistrationInfo {
        try await request(
            method: "GET",
            path: "api/actions/voter-registration",
            queryItems: [URLQueryItem(name: "state", value: state)]
        )
    }

    // MARK: Core request helper

    private struct AnyEncodable: Encodable {
        private let encodeClosure: (Encoder) throws -> Void

        init<T: Encodable>(_ value: T) {
            encodeClosure = value.encode(to:)
        }

        func encode(to encoder: Encoder) throws {
            try encodeClosure(encoder)
        }
    }

    private func request<Response: Decodable>(
        method: String,
        path: String,
        queryItems: [URLQueryItem] = [],
        body: AnyEncodable? = nil
    ) async throws -> Response {
        let baseURL = Config.baseURL.appendingPathComponent(path)
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw APIError.invalidURL
        }
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        guard let url = components.url else {
            throw APIError.invalidURL
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
            urlRequest.httpBody = try Self.encoder.encode(body)
        }

        let (data, response) = try await session.data(for: urlRequest)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.server(
                statusCode: http.statusCode,
                message: String(data: data, encoding: .utf8)
            )
        }
        return try Self.decoder.decode(Response.self, from: data)
    }

    private func request<Response: Decodable, Body: Encodable>(
        method: String,
        path: String,
        queryItems: [URLQueryItem] = [],
        body: Body
    ) async throws -> Response {
        try await request(method: method, path: path, queryItems: queryItems, body: AnyEncodable(body))
    }
}
