import { useState } from 'react';
import { Search } from 'lucide-react';

interface QueryInputProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function QueryInput({ onSearch, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState('');

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
          className="w-full px-6 py-4 pr-14 text-lg border-2 border-gray-300 rounded-xl focus:outline-none focus:border-blue-500 transition-colors shadow-sm"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Search size={24} />
        </button>
      </div>
    </form>
  );
}
