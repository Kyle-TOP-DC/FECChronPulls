import SwiftUI

struct ArticleDetailView: View {
    @EnvironmentObject private var appState: AppState
    let article: Article

    @State private var progress: Double = 0
    @State private var isLoadingPage = true
    @State private var hasPostedRead = false
    @State private var showCompose = false

    var body: some View {
        VStack(spacing: 0) {
            header

            if isLoadingPage {
                ProgressView(value: progress)
                    .progressViewStyle(.linear)
                    .tint(Color.accentColor)
            }

            if let url = article.articleURL {
                ArticleWebView(url: url, progress: $progress, isLoading: $isLoadingPage) {
                    if !hasPostedRead {
                        hasPostedRead = true
                        appState.postEvent(.read, articleID: article.id)
                    }
                }
            } else {
                ContentUnavailableView(
                    "Article unavailable",
                    systemImage: "link",
                    description: Text("This article's link could not be opened.")
                )
            }
        }
        .navigationTitle(article.source ?? "Article")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                if let url = article.articleURL {
                    ShareLink(item: url) {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .simultaneousGesture(
                        TapGesture().onEnded {
                            appState.postEvent(.share, articleID: article.id)
                        }
                    )
                }
            }
        }
        .safeAreaInset(edge: .bottom) {
            tellCongressButton
        }
        .sheet(isPresented: $showCompose) {
            ComposeMessageView(article: article)
                .environmentObject(appState)
        }
    }

    // MARK: Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(article.title)
                .font(.headline)

            HStack(spacing: 4) {
                if let source = article.source {
                    Text(source)
                    Text("·")
                }
                Text(article.displayDate, format: .dateTime.month().day().year())
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let summary = article.summary {
                Text(summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }

            if let note = article.adminNote {
                AdminNoteCallout(note: note)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal)
        .padding(.vertical, 10)
        .background(Color(uiColor: .systemBackground))
    }

    // MARK: Bottom action

    private var tellCongressButton: some View {
        Button {
            showCompose = true
        } label: {
            Text("✉️ Tell Congress what you think")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 4)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(.thinMaterial)
    }
}
