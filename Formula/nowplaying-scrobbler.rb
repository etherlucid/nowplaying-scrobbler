class NowplayingScrobbler < Formula
  desc "ListenBrainz scrobbler for YouTube Music Safari PWA and macOS MediaRemote"
  homepage "https://github.com/etherlucid/nowplaying-scrobbler"
  url "https://github.com/etherlucid/nowplaying-scrobbler/archive/refs/tags/v0.1.0-beta.2.tar.gz"
  sha256 "4e0ef102027a128e8cc44377abfec10b52f28d7e41909228150ff12669604267"
  version "0.1.0-beta.2"
  license "MIT"
  head "https://github.com/etherlucid/nowplaying-scrobbler.git", branch: "main"

  depends_on :macos

  def install
    libexec.install Dir["src"]
    libexec.install "bin/nowplaying-scrobbler"
    bin.install_symlink libexec/"nowplaying-scrobbler"
  end

  service do
    run [opt_bin/"nowplaying-scrobbler", "run"]
    keep_alive true
    log_path var/"log/nowplaying-scrobbler.log"
    error_log_path var/"log/nowplaying-scrobbler.error.log"
  end

  test do
    assert_match "nowplaying-scrobbler", shell_output("#{bin}/nowplaying-scrobbler --version")
  end
end
