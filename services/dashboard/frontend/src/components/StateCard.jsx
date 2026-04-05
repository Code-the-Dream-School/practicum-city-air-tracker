export function StateCard({
  className = "",
  icon: Icon,
  title,
  description,
  spinning = false,
  actionLabel,
  onAction,
}) {
  return (
    <div className="shell shell--centered">
      <div className={`state-card ${className}`.trim()}>
        <Icon className={spinning ? "spin" : ""} size={28} />
        <h1>{title}</h1>
        <p>{description}</p>
        {actionLabel && onAction ? (
          <button className="button button--primary" type="button" onClick={onAction}>
            {actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function LoadingState(props) {
  return <StateCard {...props} spinning />;
}

export function ErrorState(props) {
  return <StateCard {...props} className="state-card--error" />;
}

export function EmptyState(props) {
  return <StateCard {...props} />;
}
