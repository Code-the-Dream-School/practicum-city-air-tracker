export function WidgetCard({ icon: Icon, title, value, detail, tone = "sky", children }) {
  return (
    <section className={`widget-card widget-card--${tone}`}>
      <div className="widget-card__header">
        <span className="widget-card__icon">
          <Icon size={18} />
        </span>
        <span className="widget-card__title">{title}</span>
      </div>
      <div className="widget-card__value">{value}</div>
      {detail ? <div className="widget-card__detail">{detail}</div> : null}
      {children}
    </section>
  );
}
