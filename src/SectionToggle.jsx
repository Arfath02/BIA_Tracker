import React from 'react';
export default function SectionToggle({expanded,onToggle,controls,label}) {
 const action = `${expanded ? 'Collapse' : 'Expand'} ${label}`;
 return <button type="button" className="section-toggle" aria-label={action} title={action} aria-expanded={expanded} aria-controls={controls} onClick={onToggle}><span className="disclosure-chevron" aria-hidden="true"/></button>;
}
