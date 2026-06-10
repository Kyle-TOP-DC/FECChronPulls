import SwiftUI

struct ActionsView: View {
    @EnvironmentObject private var appState: AppState

    @State private var voterInfo: VoterRegistrationInfo?
    @State private var candidates: [Candidate] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                voterRegistrationSection
                candidatesSection
            }
            .navigationTitle("Take Action")
            .task {
                if voterInfo == nil && candidates.isEmpty {
                    await load()
                }
            }
            .refreshable {
                await load()
            }
        }
    }

    // MARK: Voter registration

    @ViewBuilder
    private var voterRegistrationSection: some View {
        Section {
            if let voterInfo {
                if let registerLink = voterInfo.registerLink {
                    Link(destination: registerLink) {
                        Label("Register to vote in \(voterInfo.state)", systemImage: "checkmark.square.fill")
                    }
                }
                if let checkLink = voterInfo.checkLink {
                    Link(destination: checkLink) {
                        Label("Check your registration", systemImage: "magnifyingglass")
                    }
                }
                if let note = voterInfo.note {
                    Text(note)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            } else if isLoading {
                ProgressView()
            } else if appState.usState == nil {
                Text("Look up your representatives first so we know your state.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } else if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(.red)
                Button("Retry") {
                    Task { await load() }
                }
            }
        } header: {
            Text("Register to vote")
        } footer: {
            if voterInfo != nil {
                Text("Voting is the most direct way to shape AI policy.")
            }
        }

    }

    // MARK: Candidates

    @ViewBuilder
    private var candidatesSection: some View {
        Section("Candidates who support AI safety") {
            if candidates.isEmpty && isLoading {
                ProgressView()
            } else if candidates.isEmpty {
                Text("No candidates listed right now.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(candidates) { candidate in
                    CandidateRow(candidate: candidate)
                }
            }
        }
    }

    // MARK: Loading

    private func load() async {
        isLoading = true
        errorMessage = nil

        if let state = appState.usState {
            do {
                voterInfo = try await APIClient.shared.voterRegistration(state: state)
            } catch {
                errorMessage = error.localizedDescription
            }
        }

        do {
            candidates = try await APIClient.shared.candidates()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}

// MARK: - CandidateRow

struct CandidateRow: View {
    let candidate: Candidate

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(candidate.name)
                    .font(.headline)
                Spacer()
                if let party = candidate.party {
                    TagCapsule(tag: party)
                }
            }

            Text("\(candidate.office) · \(candidate.state)")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if let blurb = candidate.blurb {
                Text(blurb)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 16) {
                if let website = candidate.websiteURL {
                    Link(destination: website) {
                        Label("Website", systemImage: "globe")
                    }
                }
                if let donate = candidate.donateLink {
                    Link(destination: donate) {
                        Label("Donate", systemImage: "heart.fill")
                    }
                }
            }
            .font(.subheadline)
            .padding(.top, 2)
        }
        .padding(.vertical, 4)
    }
}
