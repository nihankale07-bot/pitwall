import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { SessionResponse, DriversResponse, OptimizationResponse, OptimizeRequest, ActiveWorkspace } from './types';
import { Navbar } from './components/Navbar';
import { LandingPage } from './components/LandingPage';
import { IntegratedWorkspace } from './components/IntegratedWorkspace';

export function App() {
  const [inPitwall, setInPitwall] = useState<boolean>(false);
  const [currentWorkspace, setCurrentWorkspace] = useState<ActiveWorkspace>('integrated_workspace');

  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(true);
  const [loadingDrivers, setLoadingDrivers] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const [sessions, setSessions] = useState<number[]>([]);
  const [drivers, setDrivers] = useState<number[]>([]);
  const [selectedSession, setSelectedSession] = useState<number | null>(null);
  const [selectedDriver, setSelectedDriver] = useState<number | null>(null);

  const [optimizing, setOptimizing] = useState<boolean>(false);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse | null>(null);
  const [optimizationError, setOptimizationError] = useState<string | null>(null);

  useEffect(() => {
    checkBackendAndLoadSessions();
  }, []);

  const checkBackendAndLoadSessions = async () => {
    setLoadingSessions(true);
    setApiError(null);
    try {
      await api.checkHealth();
      setBackendOnline(true);

      const res: SessionResponse = await api.getSessions();
      setSessions(res.sessions || []);

      if (res.sessions && res.sessions.length > 0) {
        const firstSession = res.sessions[0];
        setSelectedSession(firstSession);
        await loadDriversForSession(firstSession);
      }
    } catch (err: any) {
      setBackendOnline(false);
      setApiError(err?.message || 'Cannot reach PITWALL FastAPI backend on 127.0.0.1:8000.');
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadDriversForSession = async (sessionKey: number) => {
    setLoadingDrivers(true);
    setApiError(null);
    try {
      const res: DriversResponse = await api.getDrivers(sessionKey);
      setDrivers(res.drivers || []);
      if (res.drivers && res.drivers.length > 0) {
        if (!selectedDriver || !res.drivers.includes(selectedDriver)) {
          setSelectedDriver(res.drivers.includes(44) ? 44 : res.drivers[0]);
        }
      } else {
        setSelectedDriver(null);
      }
    } catch (err: any) {
      setApiError(`Failed to load drivers for session ${sessionKey}: ${err?.message}`);
      setDrivers([]);
      setSelectedDriver(null);
    } finally {
      setLoadingDrivers(false);
    }
  };

  const handleSelectSession = (sessionKey: number) => {
    setSelectedSession(sessionKey);
    loadDriversForSession(sessionKey);
  };

  const handleSelectDriver = (driverNumber: number) => {
    setSelectedDriver(driverNumber);
    setOptimizationResult(null);
  };

  const handleRunOptimization = async (params: OptimizeRequest) => {
    setOptimizing(true);
    setOptimizationError(null);
    try {
      const result = await api.optimizeStrategy(params);
      setOptimizationResult(result);
    } catch (err: any) {
      setOptimizationError(err?.message || 'Strategy optimization failed.');
    } finally {
      setOptimizing(false);
    }
  };

  if (!inPitwall || !selectedSession || !selectedDriver) {
    return (
      <LandingPage
        sessions={sessions}
        drivers={drivers}
        selectedSession={selectedSession}
        selectedDriver={selectedDriver}
        loadingSessions={loadingSessions}
        loadingDrivers={loadingDrivers}
        onSelectSession={handleSelectSession}
        onSelectDriver={handleSelectDriver}
        onEnterPitwall={() => setInPitwall(true)}
        onRefresh={checkBackendAndLoadSessions}
        backendOnline={backendOnline}
        errorMessage={apiError}
      />
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <Navbar
        sessionKey={selectedSession}
        driverNumber={selectedDriver}
        currentWorkspace={currentWorkspace}
        onSelectWorkspace={(ws) => setCurrentWorkspace(ws)}
        onExitToLanding={() => setInPitwall(false)}
        backendOnline={backendOnline}
      />

      <main style={{ paddingBottom: '2.5rem' }}>
        <IntegratedWorkspace
          sessionKey={selectedSession}
          targetDriver={selectedDriver}
          onRunOptimization={handleRunOptimization}
          loading={optimizing}
          result={optimizationResult}
          error={optimizationError}
        />
      </main>
    </div>
  );
}

export default App;
