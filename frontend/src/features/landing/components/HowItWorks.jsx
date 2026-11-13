import {
  Users,
  FolderPlus,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react'

const steps = [
  {
    number: '01',
    icon: Users,
    title: 'Bring your team together.',
    description:
      'Create a workspace for your team and bring everyone into one shared place to collaborate.',
    detail: 'One shared workspace',
  },
  {
    number: '02',
    icon: FolderPlus,
    title: 'Give your work structure.',
    description:
      'Create projects, set up boards, and break bigger goals into manageable tasks.',
    detail: 'Projects and organized tasks',
  },
  {
    number: '03',
    icon: CheckCircle2,
    title: 'Keep moving forward.',
    description:
      'Assign responsibilities, track progress, and move tasks through every stage of your workflow.',
    detail: 'Visible progress for everyone',
  },
]

function HowItWorks() {
  return (
    <section className="how-section section" id="how-it-works">
      <div className="container">
        <div className="section-heading how-heading">
          <span className="section-kicker">GETTING STARTED</span>
          <h2>From scattered tasks to shared progress.</h2>
          <p>
            A simple way to bring your people, projects, and everyday work
            together.
          </p>
        </div>

        <div className="how-steps">
          {steps.map((step) => {
            const Icon = step.icon

            return (
              <article className="how-step" key={step.number}>
                <div className="how-step-top">
                  <span className="how-step-number">{step.number}</span>
                  <span className="how-step-icon">
                    <Icon size={23} strokeWidth={1.7} />
                  </span>
                </div>

                <h3>{step.title}</h3>

                <p>{step.description}</p>

                <div className="how-step-detail">
                  <span />
                  {step.detail}
                </div>
              </article>
            )
          })}
        </div>

        <div className="how-bottom-note">
          <span>One connected workflow.</span>
          <ArrowRight size={17} />
          <span>Less chaos. More clarity.</span>
        </div>
      </div>
    </section>
  )
}

export default HowItWorks
