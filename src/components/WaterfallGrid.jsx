import React from 'react';
import ContentCard from './ContentCard';

const WaterfallGrid = ({ data }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {data.map((item) => (
        <ContentCard key={item.id} item={item} />
      ))}
    </div>
  );
};

export default WaterfallGrid;