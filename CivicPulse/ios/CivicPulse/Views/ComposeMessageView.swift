import SwiftUI
import UIKit

struct ComposeMessageView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    let article: Article

    private enum Phase {
        case pickRep
        case compose
        case delivered(CongressMessage)
    }

    @State private var phase: Phase = .pickRep
    @State private var selectedRep: Representative?
    @State private var thoughts = ""
    @State private var subject = ""
    @State private var bodyText = ""
    @State private var deliveryMethod: DeliveryMethod = .webform
    @State private var isDrafting = false
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var copiedToClipboard = false

    var body: some View {
        NavigationStack {
            Group {
                switch phase {
                case .pickRep:
                    repPicker
                case .compose:
                    composeForm
                case .delivered(let message):
                    deliveryOptions(for: message)
                }
            }
            .navigationTitle("Tell Congress")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
        .onAppear {
            appState.postEvent(.actionOpen, articleID: article.id)
        }
    }

    // MARK: Step 1 — pick a representative

    private var repPicker: some View {
        List {
            Section {
                Text("Who should hear from you about “\(article.title)”?")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Section("Senators") {
                ForEach(appState.senators) { rep in
                    repButton(rep)
                }
            }

            Section("House") {
                ForEach(appState.myHouseReps) { rep in
                    repButton(rep)
                }
            }
        }
    }

    private func repButton(_ rep: Representative) -> some View {
        Button {
            selectedRep = rep
            phase = .compose
        } label: {
            HStack {
                RepRow(rep: rep)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: Step 2 — compose

    private var composeForm: some View {
        Form {
            if let rep = selectedRep {
                Section("To") {
                    HStack {
                        RepRow(rep: rep)
                        Spacer()
                        Button("Change") { phase = .pickRep }
                            .font(.subheadline)
                    }
                }
            }

            Section {
                ZStack(alignment: .topLeading) {
                    if thoughts.isEmpty {
                        Text("What do you want your representative to know?")
                            .foregroundStyle(.tertiary)
                            .padding(.top, 8)
                            .padding(.leading, 4)
                            .allowsHitTesting(false)
                    }
                    TextEditor(text: $thoughts)
                        .frame(minHeight: 110)
                }

                Button {
                    Task { await generateDraft() }
                } label: {
                    HStack {
                        if isDrafting {
                            ProgressView()
                            Text("Generating…")
                        } else {
                            Label("Generate draft", systemImage: "wand.and.stars")
                        }
                    }
                }
                .disabled(isDrafting || thoughts.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            } header: {
                Text("Your thoughts")
            } footer: {
                Text("We'll combine a summary of the article with your thoughts into a draft you can edit.")
            }

            Section("Draft") {
                TextField("Subject", text: $subject)
                ZStack(alignment: .topLeading) {
                    if bodyText.isEmpty {
                        Text("Message body")
                            .foregroundStyle(.tertiary)
                            .padding(.top, 8)
                            .padding(.leading, 4)
                            .allowsHitTesting(false)
                    }
                    TextEditor(text: $bodyText)
                        .frame(minHeight: 180)
                }
            }

            Section {
                Picker("How will you deliver it?", selection: $deliveryMethod) {
                    ForEach(DeliveryMethod.allCases) { method in
                        Text(method.label).tag(method)
                    }
                }
                .pickerStyle(.segmented)

                Button {
                    Task { await saveAndDeliver() }
                } label: {
                    HStack {
                        Spacer()
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Save & deliver").bold()
                        }
                        Spacer()
                    }
                }
                .disabled(!canSave)
            } footer: {
                Text("Replies from the office will show up in your Inbox tab.")
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

    private var canSave: Bool {
        !isSaving
            && selectedRep != nil
            && !subject.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !bodyText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    // MARK: Step 3 — deliver

    private func deliveryOptions(for message: CongressMessage) -> some View {
        List {
            Section {
                VStack(spacing: 10) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 40))
                        .foregroundStyle(.green)
                    Text("Message saved")
                        .font(.title3.bold())
                    Text("Now get it to \(message.repName)'s office:")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            }
            .listRowBackground(Color.clear)

            Section("Contact the office") {
                if let rep = selectedRep, let phoneURL = rep.phoneURL, let phone = rep.phone {
                    Link(destination: phoneURL) {
                        Label("Call \(phone)", systemImage: "phone.fill")
                    }
                }

                Button {
                    UIPasteboard.general.string = "\(message.subject)\n\n\(message.body)"
                    copiedToClipboard = true
                } label: {
                    Label(
                        copiedToClipboard ? "Copied!" : "Copy message to clipboard",
                        systemImage: copiedToClipboard ? "checkmark" : "doc.on.doc"
                    )
                }

                if let rep = selectedRep, let formURL = rep.contactFormLink {
                    Link(destination: formURL) {
                        Label("Open contact form", systemImage: "safari")
                    }
                }
            }

            Section {
                Button {
                    dismiss()
                } label: {
                    HStack {
                        Spacer()
                        Text("Done").bold()
                        Spacer()
                    }
                }
            } footer: {
                Text("If the office replies, you'll find their response in the Inbox tab.")
            }
        }
    }

    // MARK: Actions

    private func generateDraft() async {
        guard let rep = selectedRep else { return }
        isDrafting = true
        errorMessage = nil
        do {
            let draft = try await appState.generateDraft(article: article, rep: rep, thoughts: thoughts)
            subject = draft.subject
            bodyText = draft.body
        } catch {
            errorMessage = error.localizedDescription
        }
        isDrafting = false
    }

    private func saveAndDeliver() async {
        guard let rep = selectedRep else { return }
        isSaving = true
        errorMessage = nil
        do {
            let message = try await appState.sendMessage(
                article: article,
                rep: rep,
                subject: subject,
                body: bodyText,
                deliveryMethod: deliveryMethod
            )
            phase = .delivered(message)
        } catch {
            errorMessage = error.localizedDescription
        }
        isSaving = false
    }
}
