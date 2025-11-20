import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import QueryInput from './components/QueryInput';
import ResultsTable from './components/ResultsTable';
import { processQuery, type QueryResult } from './lib/queryProcessor';

function App() {
  const [results, setResults] = useState<QueryResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await processQuery(query);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-12">
        <div className="flex flex-col items-center">
          <div className="flex items-center gap-3 mb-4">
            <BookOpen size={40} className="text-blue-500" />
            <h1 className="text-4xl font-bold text-gray-900">Grade Distribution Query</h1>
          </div>

          <p className="text-gray-600 mb-12 text-center max-w-2xl">
            Search for courses by department and grade distribution thresholds using natural language queries
          </p>

          <QueryInput onSearch={handleSearch} isLoading={isLoading} />

          {isLoading && (
            <div className="mt-8 text-gray-600">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-8 w-full max-w-4xl p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {!isLoading && hasSearched && <ResultsTable results={results} />}
        </div>
      </div>
    </div>
  );
}

export default App;
