import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CourseDetail from './pages/CourseDetail';
import ComparisonPage from './pages/ComparisonPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/course/:id" element={<CourseDetail />} />
      <Route path="/compare" element={<ComparisonPage />} />
      <Route path="*" element={<HomePage />} />
    </Routes>
  );
}

export default App;
