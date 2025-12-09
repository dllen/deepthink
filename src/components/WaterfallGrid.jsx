import ContentCard from './ContentCard';

const WaterfallGrid = ({ data }) => {
  return (
    <div className="columns-1 md:columns-2 lg:columns-3 xl:columns-4 gap-6 space-y-6 px-2">
      {data.map((item) => (
        <div key={item.id} className="break-inside-avoid">
          <ContentCard item={item} />
        </div>
      ))}
    </div>
  );
};

export default WaterfallGrid;