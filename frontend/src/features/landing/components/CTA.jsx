import { ArrowUpRight, Circle, Clock3, CheckCircle2 } from 'lucide-react'

function CTA() {
  return (
    <section className="cta-section" id="get-started">
      <div className="container">
        <div className="cta-panel">
          <div className="cta-content">
            <span className="cta-kicker">
              A BETTER WAY TO WORK
            </span>

            <h2>
              Make room for
              <span> meaningful progress.</span>
            </h2>

            <p>
              Bring your team and projects together.
              Start building a more organized way to work.
            </p>

            <a href="/register" className="cta-button">
              Get started <ArrowUpRight size={18} />
            </a>
          </div>

          <div className="cta-workspace" aria-hidden="true">
            <div className="cta-workspace-header">
              <span className="cta-workspace-dots">
                <i /><i /><i />
              </span>
              <span>PROJECT OVERVIEW</span>
              <span className="cta-live"><i /> LIVE</span>
            </div>

            <div className="cta-board">
              <div className="cta-board-column">
                <div className="cta-column-heading">
                  <Circle size={13} /> To do <span>02</span>
                </div>
                <div className="cta-task">
                  <span className="cta-task-tag sand">Planning</span>
                  <strong>Define project goals</strong>
                  <small>Nov 18</small>
                </div>
                <div className="cta-task">
                  <span className="cta-task-tag green">Design</span>
                  <strong>Review wireframes</strong>
                  <small>Nov 20</small>
                </div>
              </div>

              <div className="cta-board-column">
                <div className="cta-column-heading">
                  <Clock3 size={13} /> In progress <span>01</span>
                </div>
                <div className="cta-task">
                  <span className="cta-task-tag green">Development</span>
                  <strong>Build project dashboard</strong>
                  <small>Nov 16</small>
                </div>
              </div>

              <div className="cta-board-column">
                <div className="cta-column-heading">
                  <CheckCircle2 size={13} /> Done <span>01</span>
                </div>
                <div className="cta-task">
                  <span className="cta-task-tag sand">Setup</span>
                  <strong>Create workspace</strong>
                  <small>Nov 12</small>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>
  )
}

export default CTA
