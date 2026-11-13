import {
  FolderKanban,
  LayoutDashboard,
  Users,
  ListChecks,
  MessageSquare,
  Activity,
} from 'lucide-react'

const features = [
  {
    icon: FolderKanban,
    title: 'Projects, organized',
    description:
      'Bring projects, priorities, and important details together in one organized space. Always know what needs attention.',
    tone: 'green',
  },
  {
    icon: LayoutDashboard,
    title: 'Visual Kanban boards',
    description:
      'See work move from to-do to done. Organize tasks visually and keep your team aligned on what comes next.',
    tone: 'sand',
  },
  {
    icon: Users,
    title: 'Shared workspaces',
    description:
      'Give your team a central place to plan, manage projects, and collaborate without losing context.',
    tone: 'green',
  },
  {
    icon: ListChecks,
    title: 'Clear issue tracking',
    description:
      'Create, assign, prioritize, and track issues so every task has an owner and a clear next step.',
    tone: 'sand',
  },
  {
    icon: MessageSquare,
    title: 'Team collaboration',
    description:
      'Keep conversations and updates close to the work. Less switching between tools, more shared context.',
    tone: 'green',
  },
  {
    icon: Activity,
    title: 'Progress at a glance',
    description:
      'Follow project activity and see how work is progressing, helping your team stay informed and focused.',
    tone: 'sand',
  },
]

function Features() {
  return (
    <section className="features-section section" id="features">
      <div className="container">
        <div className="section-heading features-heading">
          <span className="section-kicker">BUILT FOR TEAMWORK</span>
          <h2>Everything your team needs to move work forward.</h2>
          <p>
            From the first task to the final milestone, keep your projects
            organized and your team on the same page.
          </p>
        </div>

        <div className="features-grid">
          {features.map((feature, index) => {
            const Icon = feature.icon

            return (
              <article className="feature-card" key={feature.title}>
                <div className={`feature-icon feature-icon-${feature.tone}`}>
                  <Icon size={22} strokeWidth={1.8} />
                </div>

                <span className="feature-number">
                  0{index + 1}
                </span>

                <h3>{feature.title}</h3>
                <p>{feature.description}</p>

              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default Features