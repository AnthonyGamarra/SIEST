export default function AnioFilter({ options, value, onChange }) {
  const toggle = (val) => {
    if (val === 'TODOS') {
      onChange(['TODOS']);
      return;
    }
    let next = value.includes('TODOS') ? [] : [...value];
    if (next.includes(val)) {
      next = next.filter((v) => v !== val);
    } else {
      next = [...next, val];
    }
    onChange(next.length === 0 ? ['TODOS'] : next);
  };

  return (
    <div className="anio-filter">
      <small className="filter-label">Anio</small>
      <div className="chip-row">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`chip ${value.includes(opt.value) ? 'chip-active' : ''}`}
            onClick={() => toggle(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
