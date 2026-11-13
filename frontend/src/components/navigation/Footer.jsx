import { ArrowUpRight } from 'lucide-react'

function Footer() {
  return (
    <footer className="footer" id="footer">
      <div className="container">
        <div className="footer-main">
          <div className="footer-brand-area">
            <a href="/" className="footer-brand">NEXVIA</a>
            <p>
              Bring your team's work into focus.
              A clearer way to plan, organize, and collaborate.
            </p>
          </div>

          <div className="footer-links-group">
            <span className="footer-label">EXPLORE</span>
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#get-started">Get started</a>
          </div>

          <div className="footer-links-group">
            <span className="footer-label">ACCOUNT</span>
            <a href="/login">Log in</a>
            <a href="/register">
              Create an account <ArrowUpRight size={13} />
            </a>
          </div>
        </div>

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} NEXVIA. All rights reserved.</span>
          <span>Built for teams that move forward.</span>
        </div>
      </div>
    </footer>
  )
}

export default Footer
