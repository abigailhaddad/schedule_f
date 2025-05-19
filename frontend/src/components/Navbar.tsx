// components/Navbar.tsx
import { datasetConfig } from '@/lib/config';

export default function Navbar() {
  const { title, subtitle } = datasetConfig;
  
  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
      <div className="container-fluid">
        <a className="navbar-brand" id="navbar-title" href="#">
          {title}
        </a>
        {subtitle && (
          <div className="text-white-50" id="navbar-subtitle">
            {subtitle}
          </div>
        )}
      </div>
    </nav>
  );
}