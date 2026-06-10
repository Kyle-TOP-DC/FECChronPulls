import SwiftUI
import UIKit
import UserNotifications

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.openURL) private var openURL

    @State private var zip = ""
    @State private var name = ""
    @State private var email = ""
    @State private var isSaving = false
    @State private var saveMessage: String?
    @State private var pushStatus: UNAuthorizationStatus = .notDetermined

    var body: some View {
        NavigationStack {
            Form {
                profileSection
                notificationsSection
                aboutSection
            }
            .navigationTitle("Settings")
            .onAppear(perform: seedFields)
            .task {
                await refreshPushStatus()
            }
        }
    }

    // MARK: Profile

    private var profileSection: some View {
        Section {
            TextField("ZIP code", text: $zip)
                .keyboardType(.numberPad)
                .onChange(of: zip) { _, newValue in
                    zip = String(newValue.filter(\.isNumber).prefix(5))
                }
            TextField("Name", text: $name)
                .textContentType(.name)
            TextField("Email", text: $email)
                .keyboardType(.emailAddress)
                .textContentType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()

            Button {
                Task { await save() }
            } label: {
                HStack {
                    if isSaving {
                        ProgressView()
                    } else {
                        Text("Save changes")
                    }
                }
            }
            .disabled(isSaving || zip.count != 5 || !hasChanges)
        } header: {
            Text("Profile")
        } footer: {
            if let saveMessage {
                Text(saveMessage)
            } else {
                Text("Changing your ZIP code re-runs the representative lookup.")
            }
        }
    }

    private var hasChanges: Bool {
        guard let user = appState.user else { return false }
        return zip != user.zipCode
            || name != (user.name ?? "")
            || email != (user.email ?? "")
    }

    // MARK: Notifications

    private var notificationsSection: some View {
        Section {
            HStack {
                Label("Push notifications", systemImage: "bell.badge")
                Spacer()
                Text(pushStatusText)
                    .foregroundStyle(pushStatus == .authorized ? Color.green : Color.secondary)
            }

            Button {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    openURL(url)
                }
            } label: {
                Label("Open system settings", systemImage: "gear")
            }
        } header: {
            Text("Notifications")
        } footer: {
            Text("We send a notification when a congressional office replies to one of your messages.")
        }
    }

    private var pushStatusText: String {
        switch pushStatus {
        case .authorized: return "Enabled"
        case .provisional: return "Provisional"
        case .ephemeral: return "Ephemeral"
        case .denied: return "Disabled"
        case .notDetermined: return "Not requested"
        @unknown default: return "Unknown"
        }
    }

    // MARK: About

    private var aboutSection: some View {
        Section("About") {
            LabeledContent("Version", value: appVersion)
            LabeledContent("Backend", value: Config.baseURL.absoluteString)
        }
    }

    private var appVersion: String {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"
        return "\(version) (\(build))"
    }

    // MARK: Actions

    private func seedFields() {
        guard let user = appState.user else { return }
        zip = user.zipCode
        name = user.name ?? ""
        email = user.email ?? ""
    }

    private func save() async {
        isSaving = true
        saveMessage = nil
        do {
            try await appState.updateProfile(
                zip: zip,
                name: name.trimmingCharacters(in: .whitespacesAndNewlines),
                email: email.trimmingCharacters(in: .whitespacesAndNewlines)
            )
            saveMessage = "Saved."
        } catch {
            saveMessage = "Could not save: \(error.localizedDescription)"
        }
        isSaving = false
    }

    private func refreshPushStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        pushStatus = settings.authorizationStatus
    }
}
