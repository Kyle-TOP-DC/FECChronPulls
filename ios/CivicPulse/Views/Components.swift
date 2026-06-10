import SwiftUI

// MARK: - TagCapsule

struct TagCapsule: View {
    let tag: String

    var body: some View {
        Text(tag)
            .font(.caption2.weight(.medium))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Color.accentColor.opacity(0.12), in: Capsule())
            .foregroundStyle(Color.accentColor)
    }
}

// MARK: - StatusBadge

struct StatusBadge: View {
    let status: MessageStatus

    private var color: Color {
        switch status {
        case .drafted: return .gray
        case .sent: return .blue
        case .replied: return .green
        }
    }

    var body: some View {
        Text(status.rawValue.capitalized)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.15), in: Capsule())
            .foregroundStyle(color)
    }
}

// MARK: - RepAvatar

struct RepAvatar: View {
    let rep: Representative
    var size: CGFloat = 44

    var body: some View {
        AsyncImage(url: rep.photoLink) { phase in
            if let image = phase.image {
                image.resizable().scaledToFill()
            } else {
                Image(systemName: "person.crop.circle.fill")
                    .resizable()
                    .foregroundStyle(.tertiary)
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
    }
}

// MARK: - RepRow

struct RepRow: View {
    let rep: Representative

    var body: some View {
        HStack(spacing: 12) {
            RepAvatar(rep: rep)
            VStack(alignment: .leading, spacing: 2) {
                Text(rep.name)
                    .font(.headline)
                Text(rep.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: - AdminNoteCallout

struct AdminNoteCallout: View {
    let note: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label("From the editors", systemImage: "highlighter")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.accentColor)
            Text(note)
                .font(.subheadline)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.accentColor.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - ErrorRetryView

struct ErrorRetryView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        ContentUnavailableView {
            Label("Something went wrong", systemImage: "exclamationmark.triangle")
        } description: {
            Text(message)
        } actions: {
            Button("Retry", action: retry)
                .buttonStyle(.borderedProminent)
        }
    }
}
