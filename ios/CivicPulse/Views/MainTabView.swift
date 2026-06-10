import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        TabView {
            FeedView()
                .tabItem { Label("Feed", systemImage: "newspaper") }

            MyRepsView()
                .tabItem { Label("My Reps", systemImage: "building.columns") }

            ActionsView()
                .tabItem { Label("Actions", systemImage: "megaphone") }

            InboxView()
                .tabItem { Label("Inbox", systemImage: "envelope") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
        }
        .task {
            // Restore representative data after a cold launch.
            if appState.representatives.isEmpty {
                try? await appState.lookupReps()
            }
        }
    }
}
