export default function Panel({ title, icon, id, action, className = '', bodyClass = '', children }) {
  return (
    <section className={`panel flex h-full min-h-0 min-w-0 flex-col ${className}`}>
      <div className="panel-head">
        {icon}
        <span>{title}</span>
        {action}
        {id && <span className="badge-id">{id}</span>}
      </div>
      <div className={`min-h-0 flex-1 ${bodyClass}`}>{children}</div>
    </section>
  )
}
