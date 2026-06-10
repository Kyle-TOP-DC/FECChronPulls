import SwiftUI

struct MyRepsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if appState.myReps.isEmpty && isLoading {
                    ProgressView("Looking up your representatives…")
                } else if let errorMessage, appState.myReps.isEmpty {
                    ErrorRetryView(message: errorMessage) {
                        Task { await refresh() }
                    }
                } else if appState.myReps.isEmpty {
                    ContentUnavailableView(
                        "No representatives found",
                        systemImage: "building.columns",
                        description: Text("Check your ZIP code in Settings, then try again.")
                    )
                } else {
                    repList
                }
            }
            .navigationTitle("My Reps")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await refresh() }
                    } label: {
                        if isLoading {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(isLoading)
                }
            }
        }
    }

    private var repList: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                if let user = appState.user {
                    HStack {
                        Text("Representing ZIP \(user.zipCode)")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button("Re-run lookup") {
                            Task { await refresh() }
                        }
                        .font(.subheadline)
                    }
                    .padding(.horizontal, 4)
                }

                ForEach(appState.myReps) { rep in
                    RepCard(rep: rep)
                }
            }
            .padding()
        }
        .refreshable {
            await refresh()
        }
    }

    private func refresh() async {
        isLoading = true
        errorMessage = nil
        do {
            try await appState.lookupReps()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

// MARK: - RepCard

struct RepCard: View {
    let rep: Representative

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                RepAvatar(rep: rep, size: 56)
                VStack(alignment: .leading, spacing: 2) {
                    Text(rep.name)
                        .font(.headline)
                    Text(rep.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }

            Divider()

            VStack(alignment: .leading, spacing: 10) {
                if let phoneURL = rep.phoneURL, let phone = rep.phone {
                    Link(destination: phoneURL) {
                        Label(phone, systemImage: "phone.fill")
                    }
                }
                if let website = rep.websiteURL {
                    Link(destination: website) {
                        Label("Official website", systemImage: "globe")
                    }
                }
                if let form = rep.contactFormLink {
                    Link(destination: form) {
                        Label("Contact form", systemImage: "square.and.pencil")
                    }
                }
                if let address = rep.officeAddress {
                    Label(address, systemImage: "mappin.and.ellipse")
                        .foregroundStyle(.secondary)
                }
            }
            .font(.subheadline)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(uiColor: .secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 14))
    }
}
