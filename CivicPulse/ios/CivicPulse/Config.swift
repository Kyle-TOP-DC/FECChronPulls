import Foundation

enum Config {
    /// Base URL of the CivicPulse backend.
    ///
    /// `localhost` works from the iOS Simulator (it shares the Mac's loopback
    /// interface). When running on a physical iPhone, change this to your
    /// machine's LAN address, e.g. `http://192.168.1.20:8000`.
    static let baseURL = URL(string: "http://localhost:8000")!
}
