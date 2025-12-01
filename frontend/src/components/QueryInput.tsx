import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';

interface QueryInputProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
  initialValue?: string;
}

export default function QueryInput({ onSearch, isLoading, initialValue }: QueryInputProps) {
  const [query, setQuery] = useState(initialValue ?? '');

  // Keep input in sync with cached initial value (e.g., when returning from detail view).
  useEffect(() => {
    setQuery(initialValue ?? '');
  }, [initialValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-4xl">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try: "Give me all the Computer Science classes with above a 83% of the student population receiving Bs or above"'
          className="w-full px-6 py-4 pr-14 text-lg border-2 border-[#f2cbb3] rounded-xl focus:outline-none focus:border-[#e87722] transition-colors shadow-sm"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-[#861f41] text-white rounded-lg hover:bg-[#6f1936] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Search size={24} />
        </button>
      </div>
    </form>
  );
}
