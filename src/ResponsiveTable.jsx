import React from 'react';

// Preserve one semantic table and its controls; expose column labels in mobile cards.
export default function ResponsiveTable({children,...props}){
 const labels=[];
 const scan=nodes=>React.Children.forEach(nodes,node=>{if(!React.isValidElement(node))return;if(node.type==='th')labels.push(typeof node.props.children==='string'?node.props.children:'Actions');else scan(node.props.children)});
 scan(children);
 const walk=nodes=>React.Children.map(nodes,node=>{
  if(!React.isValidElement(node))return node;
  if(node.type==='tr'){
   let column=0;
   return React.cloneElement(node,{},React.Children.map(node.props.children,cell=>React.isValidElement(cell)&&cell.type==='td'?React.cloneElement(cell,{'data-label':labels[column++]||'Actions'}):cell));
  }
  return node.props.children?React.cloneElement(node,{},walk(node.props.children)):node;
 });
 return <table {...props}>{walk(children)}</table>;
}
