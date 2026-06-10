import SwiftUI

struct InboxView: View {
    @EnvironmentObject private var appState: AppState
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if appState.messages.isEmpty && isLoading {
                    ProgressView("Loading messages…")
                } else if let errorMessage, appState.messages.isEmpty {
                    ErrorRetryView(message: errorMessage) {
                        Task { await load() }
                    }
                } else if appState.messages.isEmpty {
                    ContentUnavailableView(
                        "No messages yet",
                        systemImage: "envelope.open",
                        description: Text("Messages you send to Congress — and any office replies — will show up here.")
                    )
                } else {
                    List(appState.messages) { message in
                        MessageRow(message: message)
                    }
                    .listStyle(.insetGrouped)
                    .refreshable {
                        await load()
                    }
                }
            }
            .navigationTitle("Inbox")
            .task {
                if appState.messages.isEmpty {
                    await load()
                }
            }
        }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            try await appState.loadMessages()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

// MARK: - MessageRow

struct MessageRow: View {
    let message: CongressMessage

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                Text(message.subject)
                    .font(.headline)
                    .lineLimit(2)
                Spacer()
                StatusBadge(status: message.status)
            }

            Text("To: \(message.repName)")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(message.createdAt, format: .relative(presentation: .named))
                .font(.caption)
                .foregroundStyle(.tertiary)

            if let reply = message.officeReply {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Reply from the office", systemImage: "arrowshape.turn.up.left.fill")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.green)
                    Text(reply)
                        .font(.subheadline)
                    if let repliedAt = message.repliedAt {
                        Text(repliedAt, format: .relative(presentation: .named))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.green.opacity(0.1), in: RoundedRectangle(cornerRadius: 10))
            }
        }
        .padding(.vertical, 4)
    }
}
