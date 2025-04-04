import React, { useState, useRef, useEffect } from 'react';
import { ResearchHistoryItem } from '../types/data';
import { formatDistanceToNow } from 'date-fns';

interface ResearchSidebarProps {
  history: ResearchHistoryItem[];
  onSelectResearch: (id: string) => void;
  onNewResearch: () => void;
  onDeleteResearch: (id: string) => void;
  isOpen: boolean;
  toggleSidebar: () => void;
}

const ResearchSidebar: React.FC<ResearchSidebarProps> = ({
  history,
  onSelectResearch,
  onNewResearch,
  onDeleteResearch,
  isOpen,
  toggleSidebar,
}) => {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isOpen && 
          sidebarRef.current && 
          !sidebarRef.current.contains(event.target as Node)) {
        toggleSidebar();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, toggleSidebar]);

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="sidebar-overlay md:hidden fixed inset-0 bg-black bg-opacity-50 z-40" 
          onClick={toggleSidebar}
          aria-hidden="true"
        />
      )}
      
      <div ref={sidebarRef} className={`fixed top-0 left-0 h-full sidebar-z-index transition-all duration-300 ${isOpen ? 'w-[85%] sm:w-[75%] md:w-[300px] max-w-[300px]' : 'w-12 sm:w-16'}`}>
        {/* Sidebar content */}
        <div 
          className={`h-full transition-all duration-300 text-white overflow-hidden 
            ${isOpen 
              ? 'bg-gray-900/70 sidebar-backdrop shadow-lg p-3 sm:p-4' 
              : 'bg-transparent hover:bg-gray-900/10 p-0'
            }`}
        >
          {/* Toggle button - only shown when sidebar is closed */}
          {!isOpen && (
            <button
              onClick={toggleSidebar}
              className="absolute left-2 sm:left-3 mx-auto top-[20px] sm:top-[24px] w-8 sm:w-10 h-8 sm:h-10 flex items-center justify-center bg-gradient-to-br from-teal-400/8 via-cyan-300/6 to-blue-400/5 text-white rounded-full shadow-sm z-10 hover:from-teal-500/90 hover:via-cyan-400/90 hover:to-blue-500/90 hover:shadow-teal-500/20 hover:shadow-xl transition-all duration-300"
              aria-label="Open sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 sm:h-6 w-5 sm:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
          )}

          {!isOpen && (
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 -rotate-90 whitespace-nowrap text-gray-600 font-medium tracking-wider text-xs">
              {" "}
            </div>
          )}

          {isOpen && (
            <>
              <div className="flex justify-between items-center mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl font-semibold">Research History</h2>
                <button
                  onClick={toggleSidebar}
                  className="w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center bg-gray-800 text-white rounded-full shadow-lg"
                  aria-label="Close sidebar"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
              </div>

              {/* New Research button */}
              <button
                onClick={onNewResearch}
                className="w-full py-2 sm:py-3 px-3 sm:px-4 mb-4 sm:mb-6 bg-teal-500 hover:bg-gradient-to-br hover:from-teal-400 hover:to-cyan-500 text-white rounded shadow hover:shadow-teal-500/20 hover:shadow-lg font-bold text-sm transition-all duration-300 flex items-center justify-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 sm:h-5 w-4 sm:w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Research
              </button>

              {/* History list */}
              <div className="overflow-y-auto sidebar-scrollbar h-[calc(100vh-150px)] sm:h-[calc(100vh-190px)]">
                {history.length === 0 ? (
                  <div className="text-center py-6 sm:py-8 text-gray-400">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-10 sm:h-12 w-10 sm:w-12 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p>No research history yet</p>
                    <p className="text-sm mt-2">Start a new research to see it here</p>
                  </div>
                ) : (
                  <ul className="space-y-1 sm:space-y-2">
                    {history.map((item) => (
                      <li 
                        key={item.id}
                        className="relative rounded-md hover:bg-gray-800 transition-colors duration-200 shadow-sm hover:shadow border-l-2 border-gray-700 hover:border-teal-500 pl-0.5"
                        onMouseEnter={() => setHoveredItem(item.id)}
                        onMouseLeave={() => setHoveredItem(null)}
                      >
                        <button
                          onClick={() => onSelectResearch(item.id)}
                          className="w-full text-left p-2 sm:p-3 pr-8 min-h-[48px]"
                        >
                          <h3 className="font-medium truncate text-gray-200 text-sm sm:text-base">{item.question}</h3>
                          <p className="text-xs text-gray-400 mt-1">
                            {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                          </p>
                        </button>
                        
                        {hoveredItem === item.id && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteResearch(item.id);
                            }}
                            className="absolute right-2 top-3 text-gray-400 hover:text-red-500 transition-colors duration-200 w-8 h-8 flex items-center justify-center"
                            aria-label="Delete research"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default ResearchSidebar; 