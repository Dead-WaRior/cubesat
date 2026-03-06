import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, PerspectiveCamera, Html, Float, Line } from '@react-three/drei';
import * as THREE from 'three';
import useDashboardStore from '../store';

/**
 * TrajectoryPath
 * Renders a glowing line based on a series of points.
 */
function TrajectoryPath({ points, color = "#3b82f6", opacity = 0.5, lineWidth = 1 }) {
    if (!points || points.length < 2) return null;
    const linePoints = points.map(p => new THREE.Vector3(p.x, p.y, p.z));
    return (
        <Line 
            points={linePoints} 
            color={color} 
            lineWidth={lineWidth} 
            transparent 
            opacity={opacity} 
            dashed={false}
        />
    );
}

/**
 * DebrisObject
 * Renders a single debris item in 3D space with interactivity.
 */
function DebrisObject({ track }) {
  const meshRef = useRef();
  const setSelectedTrackId = useDashboardStore((s) => s.setSelectedTrackId);
  const selectedTrackId = useDashboardStore((s) => s.selectedTrackId);
  
  const isSelected = String(selectedTrackId) === String(track.track_id);
  const isCritical = track.alert_level?.toLowerCase() === 'critical';

  // Derive 3D position (In real app, map ECI X,Y,Z. Here we simulate for variety)
  const position = useMemo(() => {
    const angle = (track.track_id * 45 + Date.now() / 5000) % 360;
    const rad = 6 + (track.track_id % 3);
    const x = rad * Math.cos((angle * Math.PI) / 180);
    const z = rad * Math.sin((angle * Math.PI) / 180);
    const y = Math.sin(track.track_id) * 2;
    return [x, y, z];
  }, [track.track_id]);

  useFrame((state) => {
    if (meshRef.current) {
        meshRef.current.rotation.y += 0.01;
    }
  });

  return (
    <group position={position}>
      <mesh 
        ref={meshRef}
        onClick={(e) => {
            e.stopPropagation();
            setSelectedTrackId(track.track_id);
        }}
        onPointerOver={() => (document.body.style.cursor = 'pointer')}
        onPointerOut={() => (document.body.style.cursor = 'auto')}
      >
        <sphereGeometry args={[isCritical ? 0.15 : 0.08, 16, 16]} />
        <meshStandardMaterial 
            color={isCritical ? "#ef4444" : isSelected ? "#3b82f6" : "#facc15"} 
            emissive={isCritical ? "#ef4444" : isSelected ? "#3b82f6" : "#facc15"}
            emissiveIntensity={2}
        />
      </mesh>
      
      {isSelected && (
          <mesh>
             <ringGeometry args={[0.2, 0.25, 32]} />
             <meshBasicMaterial color="#60a5fa" transparent opacity={0.5} side={THREE.DoubleSide} />
          </mesh>
      )}

      {isCritical && (
          <mesh scale={[1.5, 1.5, 1.5]}>
             <sphereGeometry args={[0.2, 16, 16]} />
             <meshBasicMaterial color="#ef4444" transparent opacity={0.2} />
          </mesh>
      )}

      <Html distanceFactor={15}>
          <div className={`px-1 py-0.5 rounded bg-black/60 text-[8px] font-mono whitespace-nowrap transition-opacity ${isSelected ? 'opacity-100' : 'opacity-40'}`}>
              #{track.track_id}
          </div>
      </Html>

      {isSelected && track.prediction_path && (
          <TrajectoryPath points={track.prediction_path} color={isCritical ? "#ef4444" : "#3b82f6"} opacity={0.6} lineWidth={2} />
      )}
    </group>
  );
}

/**
 * Satellite
 * Renders the CubeSat itself in the 3D scene.
 */
function Satellite() {
  const satLla = useDashboardStore((s) => s.satLla);
  const satPath = useDashboardStore((s) => s.satPath);
  const hypotheticalPath = useDashboardStore((s) => s.hypotheticalPath);
  const isSimulating = useDashboardStore((s) => s.isSimulating);
  
  const position = useMemo(() => {
    if (!satPath || satPath.length === 0) return [0, 6, 0];
    const p = satPath[0];
    return [p.x, p.y, p.z];
  }, [satPath]);

  return (
      <group>
          <mesh position={position}>
              <boxGeometry args={[0.2, 0.2, 0.2]} />
              <meshStandardMaterial color="#60a5fa" emissive="#3b82f6" emissiveIntensity={2} />
              <Html distanceFactor={10}>
                  <div className="px-1 py-0.5 rounded border border-blue-500/50 bg-blue-900/80 text-[8px] font-black text-white uppercase whitespace-nowrap">
                      SENTINEL-1
                  </div>
              </Html>
          </mesh>
          <TrajectoryPath points={satPath} color="#60a5fa" opacity={0.3} lineWidth={1} />
          
          {isSimulating && hypotheticalPath && (
              <TrajectoryPath points={hypotheticalPath} color="#38bdf8" opacity={0.8} lineWidth={3} />
          )}
      </group>
  );
}

/**
 * Earth
 * Renders a glowing 3D Earth fragment.
 */
function Earth() {
  return (
    <group>
      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
        <mesh>
          <sphereGeometry args={[4, 64, 64]} />
          <meshStandardMaterial 
            color="#1e3a8a" 
            metalness={0.8} 
            roughness={0.2} 
            transparent 
            opacity={0.9}
            emissive="#1e40af"
            emissiveIntensity={0.5}
          />
        </mesh>
        {/* Glow halo */}
        <mesh scale={[1.1, 1.1, 1.1]}>
          <sphereGeometry args={[4, 32, 32]} />
          <meshBasicMaterial color="#3b82f6" transparent opacity={0.05} side={THREE.BackSide} />
        </mesh>
      </Float>
    </group>
  );
}

/**
 * OrbitalView (3D Version)
 */
function OrbitalView() {
  const tracks = useDashboardStore((s) => s.tracks);

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg flex flex-col h-full relative group">
      <div className="glass-header z-10">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          Orbital Awareness <span className="text-blue-500 font-black ml-1">3D</span>
        </h2>
        <div className="flex gap-4 items-center">
            <span className="text-[9px] font-mono text-gray-500">ZOOM: SCROLL / ROTATE: DRAG</span>
            <span className="text-[10px] font-mono text-blue-400 italic">J2000 FRAME</span>
        </div>
      </div>

      <div className="flex-1 relative min-h-[400px] bg-[#020617]">
        <Canvas shadows gl={{ antialias: true }}>
          <PerspectiveCamera makeDefault position={[10, 8, 15]} fov={45} />
          <OrbitControls 
            enableDamping 
            dampingFactor={0.05} 
            minDistance={8} 
            maxDistance={50}
            autoRotate
            autoRotateSpeed={0.5}
          />
          
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1.5} color="#3b82f6" />
          <pointLight position={[-10, -10, -10]} intensity={0.5} color="#1e40af" />
          
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          
          <Suspense fallback={null}>
            <Earth />
            <Satellite />
            {tracks.map((track) => (
              <DebrisObject key={track.track_id} track={track} />
            ))}
          </Suspense>
        </Canvas>

        {/* Legend Overlay */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-1 z-10">
            {useDashboardStore.getState().isSimulating && (
                <div className="mb-2 px-2 py-1 bg-blue-600/20 border border-blue-500/50 rounded flex items-center gap-2 animate-pulse">
                    <div className="w-2 h-2 rounded-full bg-blue-400 shadow-[0_0_5px_#38bdf8]" />
                    <span className="text-[9px] text-blue-400 uppercase font-black tracking-widest">Projection Active</span>
                </div>
            )}
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#ef4444] shadow-[0_0_5px_#ef4444]" />
                <span className="text-[8px] text-gray-400 uppercase font-black">Critical Conflict</span>
            </div>
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#3b82f6] shadow-[0_0_5px_#3b82f6]" />
                <span className="text-[8px] text-gray-400 uppercase font-black">Selected Node</span>
            </div>
        </div>
      </div>

      <div className="px-4 py-2 bg-black/40 border-t border-white/5 flex justify-between items-center z-10">
          <div className="flex flex-col">
              <span className="text-[8px] text-gray-600 font-black uppercase">Active Nodes</span>
              <span className="text-xs font-mono text-gray-300">{tracks.length} OBJECTS</span>
          </div>
          <div className="flex flex-col items-end">
              <span className="text-[8px] text-gray-600 font-black uppercase">Field Depth</span>
              <span className="text-xs font-mono text-blue-500 uppercase">Interactive</span>
          </div>
      </div>
    </div>
  );
}

export default OrbitalView;
