import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Circle,
  CircleCheck,
  Clock3,
  Plus,
  Search,
  SlidersHorizontal,
  Users,
} from 'lucide-react'

const tasks = {
  todo: [
    { title: 'Finalize onboarding flow', tag: 'Design', color: 'sand', date: 'Nov 18' },
    { title: 'Review API documentation', tag: 'Development', color: 'green', date: 'Nov 19' },
  ],
  progress: [
    { title: 'Build workspace dashboard', tag: 'Development', color: 'green', date: 'Nov 16' },
    { title: 'Prepare product walkthrough', tag: 'Planning', color: 'sand', date: 'Nov 17' },
  ],
  done: [
    { title: 'Set up project workspace', tag: 'Setup', color: 'green', date: 'Nov 12' },
  ],
}

function TaskCard({ task }) {
  return (
    <div className="preview-task">
      <span className={`task-tag task-tag-${task.color}`}>{task.tag}</span>
      <h4>{task.title}</h4>
      <div className="preview-task-meta">
        <span><CalendarDays size={12} /> {task.date}</span>
        <span className="task-avatar">JD</span>
      </div>
    </div>
  )
}

function BoardColumn({ title, count, status, items }) {
  return (
    <div className="preview-column">
      <div className="preview-column-heading">
        <div>
          {status === 'done'
            ? <CircleCheck size={14} />
            : status === 'progress'
              ? <Clock3 size={14} />
              : <Circle size={14} />}
          <span>{title}</span>
        </div>
        <span className="column-count">{count}</span>
      </div>

      {items.map((task) => (
        <TaskCard key={task.title} task={task} />
      ))}

      <button className="preview-add-task">
        <Plus size={13} /> Add task
      </button>
    </div>
  )
}

function ProductPreview() {
  return (
    <div className="hero-visual">
      <div className="preview-window">
        <div className="preview-topbar">
          <div className="preview-dots">
            <span /><span /><span />
          </div>
          <span className="preview-topbar-title">nexvia.app</span>
          <span className="preview-live"><span /> Live workspace</span>
        </div>

        <div className="preview-content">
          <aside className="preview-sidebar">
            <div className="preview-workspace">
              <span className="preview-workspace-icon">N</span>
              <div>
                <strong>Northstar Studio</strong>
                <small>Workspace</small>
              </div>
            </div>

            <div className="preview-side-label">WORKSPACE</div>
            <div className="preview-side-link active"><SlidersHorizontal size={14} /> Overview</div>
            <div className="preview-side-link"><Users size={14} /> Members</div>
            <div className="preview-side-label">YOUR PROJECTS</div>
            <div className="preview-project-link"><span className="project-dot green-dot" /> Website Redesign</div>
            <div className="preview-project-link"><span className="project-dot sand-dot" /> Mobile App</div>
          </aside>

          <div className="preview-board">
            <div className="preview-board-header">
              <div>
                <div className="preview-breadcrumb">Projects / Website Redesign</div>
                <h3>Website Redesign</h3>
                <p>Keep the team moving forward.</p>
              </div>
              <div className="preview-board-actions">
                <span className="preview-member">JD</span>
                <span className="preview-member second">AM</span>
                <button><Plus size={15} /></button>
              </div>
            </div>

            <div className="preview-board-toolbar">
              <span><Search size={13} /> Search tasks</span>
              <span><SlidersHorizontal size={13} /> Filter</span>
            </div>

            <div className="preview-columns">
              <BoardColumn title="To do" count="2" status="todo" items={tasks.todo} />
              <BoardColumn title="In progress" count="2" status="progress" items={tasks.progress} />
              <BoardColumn title="Done" count="1" status="done" items={tasks.done} />
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}

function Hero() {
  return (
    <section className="hero-section">
      <div className="container hero-grid">
        <div className="hero-copy">
          <h1>
            Bring your team's work
            <span> into focus.</span>
          </h1>

          <p className="hero-description">
            Plan projects, organize tasks, and keep everyone moving
            in the same direction. All your team's work, connected
            in one place.
          </p>

          <div className="hero-actions">
            <a href="/register" className="button button-primary">
              Get started <ArrowRight size={17} />
            </a>
            <a href="#features" className="hero-secondary-link">
              Explore features <ArrowUpRight size={16} />
            </a>
          </div>

          <div className="hero-trust">
            <span className="trust-icon"><Users size={16} /></span>
            <span>One workspace. Every project. One team.</span>
          </div>
        </div>

        <ProductPreview />
      </div>
    </section>
  )
}

export default Hero