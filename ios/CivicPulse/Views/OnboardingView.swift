import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject private var appState: AppState

    private enum Step {
        case welcome
        case confirmReps
    }

    @State private var step: Step = .welcome
    @State private var zip = ""
    @State private var name = ""
    @State private var email = ""
    @State private var selectedHouseRepID: String?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                switch step {
                case .welcome:
                    welcomeForm
                case .confirmReps:
                    repsConfirmation
                }
            }
            .navigationTitle("CivicPulse")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    // MARK: Welcome

    private var welcomeForm: some View {
        Form {
            Section {
                VStack(spacing: 12) {
                    Image(systemName: "megaphone.fill")
                        .font(.system(size: 44))
                        .foregroundStyle(Color.accentColor)
                    Text("Welcome to CivicPulse")
                        .font(.title2.bold())
                    Text("Read curated news on AI policy, then make your voice heard in Congress.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            }
            .listRowBackground(Color.clear)

            Section("Your ZIP code") {
                TextField("e.g. 94110", text: $zip)
                    .keyboardType(.numberPad)
                    .onChange(of: zip) { _, newValue in
                        zip = String(newValue.filter(\.isNumber).prefix(5))
                    }
            }

            Section {
                TextField("Name (optional)", text: $name)
                    .textContentType(.name)
                TextField("Email (optional)", text: $email)
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            } footer: {
                Text("Your name and email let congressional offices reply to you directly.")
            }

            Section {
                Button {
                    Task { await register() }
                } label: {
                    HStack {
                        Spacer()
                        if isLoading {
                            ProgressView()
                        } else {
                            Text("Get started").bold()
                        }
                        Spacer()
                    }
                }
                .disabled(zip.count != 5 || isLoading)
            }

            if let errorMessage {
                Section {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
        }
    }

    // MARK: Reps confirmation

    private var repsConfirmation: some View {
        Form {
            Section {
                Text("Here's who represents ZIP \(zip):")
                    .font(.headline)
            }
            .listRowBackground(Color.clear)

            Section("Your senators") {
                ForEach(appState.senators) { rep in
                    RepRow(rep: rep)
                }
            }

            Section {
                ForEach(appState.houseReps) { rep in
                    if needsDistrictChoice {
                        Button {
                            selectedHouseRepID = rep.bioguideID
                        } label: {
                            HStack {
                                RepRow(rep: rep)
                                Spacer()
                                if selectedHouseRepID == rep.bioguideID {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(Color.accentColor)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    } else {
                        RepRow(rep: rep)
                    }
                }
            } header: {
                Text("Your House member")
            } footer: {
                if needsDistrictChoice {
                    Text("Your ZIP code spans multiple congressional districts. Tap the member who represents your address.")
                }
            }

            Section {
                Button {
                    appState.completeOnboarding(
                        houseRepID: selectedHouseRepID ?? appState.houseReps.first?.bioguideID
                    )
                } label: {
                    HStack {
                        Spacer()
                        Text("Looks right — continue").bold()
                        Spacer()
                    }
                }
                .disabled(needsDistrictChoice && selectedHouseRepID == nil)

                Button("Use a different ZIP code") {
                    step = .welcome
                }
            }
        }
    }

    private var needsDistrictChoice: Bool {
        appState.houseReps.count > 1
    }

    // MARK: Actions

    private func register() async {
        isLoading = true
        errorMessage = nil
        do {
            try await appState.register(zip: zip, name: name, email: email)
            step = .confirmReps
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
