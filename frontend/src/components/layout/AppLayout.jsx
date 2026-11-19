
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Outlet, useLocation } from "react-router-dom";
import { X } from "lucide-react";

import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useWorkspace } from "../../context/WorkspaceContext";

const NavigationStateContext = createContext(null);

function NavigationStateProvider({ children }) {
  const location = useLocation();
  const pageStates = useRef(new Map());
  const scrollPositions = useRef(new Map());
  const activeLocationKey = useRef(location.key);

  const getPageState = useCallback(
    (key) => pageStates.current.get(key),
    []
  );

  const savePageState = useCallback((key, value) => {
    pageStates.current.set(key, value);
  }, []);

  // Continuously save the current page's proportional scroll position.
  useEffect(() => {
    const saveScrollPosition = () => {
      const maxScroll =
        document.documentElement.scrollHeight - window.innerHeight;

      const ratio =
        maxScroll > 0 ? window.scrollY / maxScroll : 0;

      scrollPositions.current.set(activeLocationKey.current, ratio);
    };

    window.addEventListener("scroll", saveScrollPosition, {
      passive: true,
    });

    return () => {
      window.removeEventListener("scroll", saveScrollPosition);
    };
  }, []);

  // Restore the proportional scroll position when navigating between pages.
  useLayoutEffect(() => {
    activeLocationKey.current = location.key;

    const savedRatio = scrollPositions.current.get(location.key);

    if (savedRatio === undefined || savedRatio === 0) {
      window.scrollTo(0, 0);
      return;
    }

    let cancelled = false;

    const restoreScroll = () => {
      if (cancelled) return;

      const maxScroll = Math.max(
        0,
        document.documentElement.scrollHeight - window.innerHeight
      );

      window.scrollTo(0, maxScroll * savedRatio);
    };

    // Restore immediately, then again as asynchronously loaded content changes height.
    restoreScroll();

    const observer = new ResizeObserver(restoreScroll);

    observer.observe(document.documentElement);

    if (document.body) {
      observer.observe(document.body);
    }

    // Stop automatic restoration when the user starts interacting.
    const cancelRestore = () => {
      cancelled = true;
      observer.disconnect();
      removeInteractionListeners();
    };

    const interactionEvents = [
      "wheel",
      "touchstart",
      "pointerdown",
      "keydown",
    ];

    const removeInteractionListeners = () => {
      interactionEvents.forEach((event) => {
        window.removeEventListener(event, cancelRestore);
      });
    };

    interactionEvents.forEach((event) => {
      window.addEventListener(event, cancelRestore, {
        passive: true,
      });
    });

    return () => {
      cancelled = true;
      observer.disconnect();
      removeInteractionListeners();
    };
  }, [location.key]);

  const value = useMemo(
    () => ({ getPageState, savePageState }),
    [getPageState, savePageState]
  );

  return (
    <NavigationStateContext.Provider value={value}>
      {children}
    </NavigationStateContext.Provider>
  );
}

export function useNavigationPageState(key, initialState) {
  const manager = useContext(NavigationStateContext);

  const [state, setState] = useState(
    () => manager?.getPageState(key) ?? initialState
  );

  const updateState = useCallback(
    (nextValue) => {
      setState((currentValue) => {
        const nextState =
          typeof nextValue === "function"
            ? nextValue(currentValue)
            : nextValue;

        manager?.savePageState(key, nextState);
        return nextState;
      });
    },
    [key, manager]
  );

  return [state, updateState];
}

function AppLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { selectedWorkspaceId } = useWorkspace();

  function closeMobileMenu() {
    setMobileMenuOpen(false);
  }

  return (
    <div className="app-layout">
      {mobileMenuOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          onClick={closeMobileMenu}
          aria-label="Close navigation"
        />
      )}

      <div
        className={`app-sidebar-wrapper ${
          mobileMenuOpen ? "app-sidebar-wrapper-open" : ""
        }`}
      >
        <div className="mobile-sidebar-header">
          <span>NEXVIA</span>
          <button
            type="button"
            onClick={closeMobileMenu}
            aria-label="Close navigation"
          >
            <X size={21} />
          </button>
        </div>

        <Sidebar onNavigate={closeMobileMenu} />
      </div>

      <div className="app-main">
        <Topbar onMenuClick={() => setMobileMenuOpen(true)} />

        <main className="app-content">
          <NavigationStateProvider
            key={selectedWorkspaceId || "no-workspace"}
          >
            <Outlet />
          </NavigationStateProvider>
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
