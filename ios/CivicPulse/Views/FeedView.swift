import SwiftUI

struct FeedView: View {
    @EnvironmentObject private var appState: AppState
    @State private var path = NavigationPath()
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack(path: $path) {
            content
                .navigationTitle("CivicPulse")
                .navigationDestination(for: Article.self) { article in
                    ArticleDetailView(article: article)
                }
                .task {
                    if appState.articles.isEmpty {
                        await load()
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        if appState.articles.isEmpty && isLoading {
            ProgressView("Loading articles…")
        } else if let errorMessage, appState.articles.isEmpty {
            ErrorRetryView(message: errorMessage) {
                Task { await load() }
            }
        } else if appState.articles.isEmpty {
            ContentUnavailableView(
                "No articles yet",
                systemImage: "newspaper",
                description: Text("Check back soon — the editors are curating stories.")
            )
        } else {
            List(appState.articles) { article in
                Button {
                    appState.postEvent(.view, articleID: article.id)
                    path.append(article)
                } label: {
                    ArticleRow(article: article)
                }
                .buttonStyle(.plain)
            }
            .listStyle(.plain)
            .refreshable {
                await load()
            }
        }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            try await appState.loadFeed()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

// MARK: - ArticleRow

struct ArticleRow: View {
    let article: Article

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                if article.imageLink != nil {
                    AsyncImage(url: article.imageLink) { phase in
                        if let image = phase.image {
                            image.resizable().scaledToFill()
                        } else {
                            Rectangle().fill(Color(uiColor: .secondarySystemBackground))
                                .overlay {
                                    Image(systemName: "photo")
                                        .foregroundStyle(.tertiary)
                                }
                        }
                    }
                    .frame(width: 72, height: 72)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(article.title)
                        .font(.headline)
                        .lineLimit(3)
                    HStack(spacing: 4) {
                        if let source = article.source {
                            Text(source)
                            Text("·")
                        }
                        Text(article.displayDate, format: .relative(presentation: .named))
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
            }

            if let note = article.adminNote {
                AdminNoteCallout(note: note)
            }

            if !article.tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(article.tags, id: \.self) { tag in
                            TagCapsule(tag: tag)
                        }
                    }
                }
            }
        }
        .padding(.vertical, 6)
    }
}
