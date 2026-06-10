import Foundation

// MARK: - User

struct User: Codable, Identifiable, Hashable {
    let id: Int
    let deviceID: String
    var zipCode: String
    var name: String?
    var email: String?
    var phone: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case deviceID = "device_id"
        case zipCode = "zip_code"
        case name
        case email
        case phone
        case createdAt = "created_at"
    }
}

// MARK: - Representatives

enum RepRole: String, Codable, Hashable {
    case senator
    case representative

    var title: String {
        switch self {
        case .senator: return "Senator"
        case .representative: return "Representative"
        }
    }
}

struct Representative: Codable, Identifiable, Hashable {
    let bioguideID: String
    let name: String
    let role: RepRole
    let party: String?
    let state: String
    let district: Int?
    let phone: String?
    let contactFormURL: String?
    let website: String?
    let officeAddress: String?
    let photoURL: String?

    var id: String { bioguideID }

    enum CodingKeys: String, CodingKey {
        case bioguideID = "bioguide_id"
        case name
        case role
        case party
        case state
        case district
        case phone
        case contactFormURL = "contact_form_url"
        case website
        case officeAddress = "office_address"
        case photoURL = "photo_url"
    }

    /// e.g. "Senator · D · CA" or "Representative · R · TX-21"
    var subtitle: String {
        var parts = [role.title]
        if let party, !party.isEmpty { parts.append(party) }
        if let district {
            parts.append("\(state)-\(district)")
        } else {
            parts.append(state)
        }
        return parts.joined(separator: " · ")
    }

    var phoneURL: URL? {
        guard let phone else { return nil }
        let digits = phone.filter { $0.isNumber || $0 == "+" }
        guard !digits.isEmpty else { return nil }
        return URL(string: "tel:\(digits)")
    }

    var websiteURL: URL? { website.flatMap(URL.init(string:)) }
    var contactFormLink: URL? { contactFormURL.flatMap(URL.init(string:)) }
    var photoLink: URL? { photoURL.flatMap(URL.init(string:)) }
}

struct RepLookupResponse: Codable, Hashable {
    let zip: String
    let state: String
    let districts: [Int]
    let representatives: [Representative]
}

// MARK: - Articles

struct Article: Codable, Identifiable, Hashable {
    let id: Int
    let title: String
    let source: String?
    let url: String
    let summary: String?
    let adminNote: String?
    let imageURL: String?
    let tags: [String]
    let published: Bool
    let publishedAt: Date?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case source
        case url
        case summary
        case adminNote = "admin_note"
        case imageURL = "image_url"
        case tags
        case published
        case publishedAt = "published_at"
        case createdAt = "created_at"
    }

    var articleURL: URL? { URL(string: url) }
    var imageLink: URL? { imageURL.flatMap(URL.init(string:)) }
    var displayDate: Date { publishedAt ?? createdAt }
}

enum EngagementEvent: String, Codable {
    case view
    case read
    case share
    case actionOpen = "action_open"
}

// MARK: - Messages

enum MessageStatus: String, Codable, Hashable {
    case drafted
    case sent
    case replied
}

enum DeliveryMethod: String, Codable, CaseIterable, Identifiable {
    case call
    case email
    case webform

    var id: String { rawValue }

    var label: String {
        switch self {
        case .call: return "Phone call"
        case .email: return "Email"
        case .webform: return "Web form"
        }
    }
}

struct MessageDraft: Codable, Hashable {
    let subject: String
    let body: String
}

struct CongressMessage: Codable, Identifiable, Hashable {
    let id: Int
    let userID: Int
    let articleID: Int?
    let repBioguideID: String
    let repName: String
    let subject: String
    let body: String
    let deliveryMethod: String
    let status: MessageStatus
    let officeReply: String?
    let repliedAt: Date?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case userID = "user_id"
        case articleID = "article_id"
        case repBioguideID = "rep_bioguide_id"
        case repName = "rep_name"
        case subject
        case body
        case deliveryMethod = "delivery_method"
        case status
        case officeReply = "office_reply"
        case repliedAt = "replied_at"
        case createdAt = "created_at"
    }
}

// MARK: - Actions

struct Candidate: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let office: String
    let state: String
    let party: String?
    let blurb: String?
    let website: String?
    let donateURL: String?
    let photoURL: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case office
        case state
        case party
        case blurb
        case website
        case donateURL = "donate_url"
        case photoURL = "photo_url"
    }

    var websiteURL: URL? { website.flatMap(URL.init(string:)) }
    var donateLink: URL? { donateURL.flatMap(URL.init(string:)) }
}

struct VoterRegistrationInfo: Codable, Hashable {
    let state: String
    let registerURL: String
    let checkURL: String
    let note: String?

    enum CodingKeys: String, CodingKey {
        case state
        case registerURL = "register_url"
        case checkURL = "check_url"
        case note
    }

    var registerLink: URL? { URL(string: registerURL) }
    var checkLink: URL? { URL(string: checkURL) }
}

struct OKResponse: Codable {
    let ok: Bool
}
