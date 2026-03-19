export function StatPill({ label, value, icon: Icon }) {
  return (
    <div className="stat-pill">
      <span className="stat-pill__icon">
        <Icon size={16} />
      </span>
      <div>
        <div className="stat-pill__label">{label}</div>
        <div className="stat-pill__value">{value}</div>
      </div>
    </div>
  );
}
