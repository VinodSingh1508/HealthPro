import { NavLink, Route, Routes } from "react-router-dom";
import Lookup from "./pages/Lookup.jsx";
import People from "./pages/People.jsx";
import DailyLog from "./pages/DailyLog.jsx";
import Trends from "./pages/Trends.jsx";
import RecipeGenerator from "./pages/RecipeGenerator.jsx";
import SavedRecipes from "./pages/SavedRecipes.jsx";

export default function App() {
  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>HealthPro</h1>
          <p className="muted">Personal food log. Numbers from tables, not from a chatbot.</p>
        </div>
        <nav>
          <NavLink to="/" end>
            Food lookup
          </NavLink>
          <NavLink to="/people">People</NavLink>
          <NavLink to="/log">Daily log</NavLink>
          <NavLink to="/trends">Trends</NavLink>
          <NavLink to="/recipes/generate">Recipe generator</NavLink>
          <NavLink to="/recipes">Saved recipes</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Lookup />} />
          <Route path="/people" element={<People />} />
          <Route path="/log" element={<DailyLog />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/recipes/generate" element={<RecipeGenerator />} />
          <Route path="/recipes" element={<SavedRecipes />} />
        </Routes>
      </main>
    </div>
  );
}
