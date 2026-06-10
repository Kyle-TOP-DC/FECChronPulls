import Foundation
import UIKit

@MainActor
final class AppState: ObservableObject {

    // MARK: Published state

    @Published private(set) var user: User?
    @Published private(set) var representatives: [Representative] = []
    @Published private(set) var usState: String?
    @Published private(set) var districts: [Int] = []
    @Published private(set) var articles: [Article] = []
    @Published private(set) var messages: [CongressMessage] = []
    @Published private(set) var selectedHouseRepID: String?
    @Published private(set) var isOnboarded: Bool = false

    // MARK: Private

    private let api = APIClient.shared
    private let defaults = UserDefaults.standard
    private var pendingDeviceToken: String?
    private var tokenObserver: NSObjectProtocol?

    private enum Keys {
        static let user = "civicpulse.user"
        static let isOnboarded = "civicpulse.isOnboarded"
        static let deviceID = "civicpulse.deviceID"
        static let houseRepID = "civicpulse.houseRepID"
        static let usState = "civicpulse.usState"
    }

    // MARK: Init

    init() {
        if let data = defaults.data(forKey: Keys.user),
           let savedUser = try? APIClient.decoder.decode(User.self, from: data) {
            user = savedUser
        }
        isOnboarded = defaults.bool(forKey: Keys.isOnboarded) && user != nil
        selectedHouseRepID = defaults.string(forKey: Keys.houseRepID)
        usState = defaults.string(forKey: Keys.usState)

        tokenObserver = NotificationCenter.default.addObserver(
            forName: .civicPulseDeviceToken,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let token = notification.object as? String else { return }
            Task { @MainActor [weak self] in
                await self?.sendDeviceToken(token)
            }
        }
    }

    deinit {
        if let tokenObserver {
            NotificationCenter.default.removeObserver(tokenObserver)
        }
    }

    // MARK: Device identity

    var deviceID: String {
        if let existing = defaults.string(forKey: Keys.deviceID) {
            return existing
        }
        let id = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        defaults.set(id, forKey: Keys.deviceID)
        return id
    }

    // MARK: Derived representatives

    var senators: [Representative] {
        representatives.filter { $0.role == .senator }
    }

    var houseReps: [Representative] {
        representatives.filter { $0.role == .representative }
    }

    /// Senators plus the user's chosen house member (or all house members for
    /// the zip if no choice has been made).
    var myReps: [Representative] {
        senators + myHouseReps
    }

    var myHouseReps: [Representative] {
        if let selectedHouseRepID,
           let chosen = houseReps.first(where: { $0.bioguideID == selectedHouseRepID }) {
            return [chosen]
        }
        return houseReps
    }

    // MARK: Registration & profile

    func register(zip: String, name: String?, email: String?) async throws {
        let registered = try await api.register(
            deviceID: deviceID,
            zipCode: zip,
            name: name?.nilIfBlank,
            email: email?.nilIfBlank,
            phone: nil
        )
        user = registered
        persistUser()
        try await lookupReps()
        if let pendingDeviceToken {
            await sendDeviceToken(pendingDeviceToken)
        }
    }

    func updateProfile(zip: String?, name: String?, email: String?) async throws {
        guard let currentUser = user else { return }
        let updated = try await api.updateUser(
            id: currentUser.id,
            zipCode: zip,
            name: name,
            email: email
        )
        let zipChanged = updated.zipCode != currentUser.zipCode
        user = updated
        persistUser()
        if zipChanged {
            setSelectedHouseRep(nil)
            try await lookupReps()
        }
    }

    func completeOnboarding(houseRepID: String?) {
        if let houseRepID {
            setSelectedHouseRep(houseRepID)
        }
        isOnboarded = true
        defaults.set(true, forKey: Keys.isOnboarded)
    }

    func setSelectedHouseRep(_ bioguideID: String?) {
        selectedHouseRepID = bioguideID
        if let bioguideID {
            defaults.set(bioguideID, forKey: Keys.houseRepID)
        } else {
            defaults.removeObject(forKey: Keys.houseRepID)
        }
    }

    // MARK: Representatives

    func lookupReps() async throws {
        guard let user else { return }
        let result = try await api.lookupReps(zip: user.zipCode)
        representatives = result.representatives
        usState = result.state
        districts = result.districts
        defaults.set(result.state, forKey: Keys.usState)

        // Drop a saved house-rep choice that no longer matches the lookup.
        if let selectedHouseRepID,
           !result.representatives.contains(where: { $0.bioguideID == selectedHouseRepID }) {
            setSelectedHouseRep(nil)
        }
    }

    // MARK: Feed

    func loadFeed() async throws {
        articles = try await api.articles(limit: 50, offset: 0)
    }

    func postEvent(_ event: EngagementEvent, articleID: Int) {
        guard let user else { return }
        Task {
            try? await api.postEvent(articleID: articleID, userID: user.id, event: event)
        }
    }

    // MARK: Messages

    func loadMessages() async throws {
        guard let user else { return }
        messages = try await api.messages(userID: user.id)
    }

    func generateDraft(article: Article, rep: Representative, thoughts: String) async throws -> MessageDraft {
        guard let user else { throw APIError.invalidResponse }
        return try await api.draftMessage(
            userID: user.id,
            articleID: article.id,
            repBioguideID: rep.bioguideID,
            thoughts: thoughts
        )
    }

    func sendMessage(
        article: Article?,
        rep: Representative,
        subject: String,
        body: String,
        deliveryMethod: DeliveryMethod
    ) async throws -> CongressMessage {
        guard let user else { throw APIError.invalidResponse }
        let message = try await api.createMessage(
            userID: user.id,
            articleID: article?.id,
            repBioguideID: rep.bioguideID,
            subject: subject,
            body: body,
            deliveryMethod: deliveryMethod
        )
        messages.insert(message, at: 0)
        return message
    }

    // MARK: Push

    func sendDeviceToken(_ token: String) async {
        guard let user else {
            pendingDeviceToken = token
            return
        }
        pendingDeviceToken = nil
        try? await api.sendDeviceToken(userID: user.id, token: token)
    }

    // MARK: Persistence

    private func persistUser() {
        guard let user, let data = try? APIClient.encoder.encode(user) else { return }
        defaults.set(data, forKey: Keys.user)
    }
}

private extension String {
    var nilIfBlank: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
