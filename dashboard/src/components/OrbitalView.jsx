import React, { Suspense, useMemo, useRef, useState } from 'react';
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
  const isSimulating = useDashboardStore((s) => s.isSimulating);

  const isSelected = String(selectedTrackId) === String(track.track_id);
  const alertLevel = (track.alert_level || 'nominal').toLowerCase();
  const isCritical = alertLevel === 'critical' && !isSimulating;
  const isWarning = alertLevel === 'warning' && !isSimulating;
  const color = isCritical ? "#ef4444" : isWarning ? "#facc15" : "#22c55e";

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
          color={color}
          emissive={color}
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
        <div className={`px-1 py-0.5 rounded bg-black/60 text-[8px] font-mono whitespace-nowrap transition-opacity flex flex-col items-center gap-0.5 ${isSelected ? 'opacity-100 z-50' : 'opacity-60'}`}>
          <span className={`font-bold ${isCritical ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-green-400'}`}>ID-{track.track_id}</span>
          {isSelected && <span className="text-gray-300">Dist: {(track.miss_distance_km ? track.miss_distance_km * 1000 : 430).toFixed(0)}m</span>}
        </div>
      </Html>

      {track.prediction_path && (
        <TrajectoryPath points={track.prediction_path} color={isCritical ? "#ef4444" : "#3b82f6"} opacity={isSelected ? 0.9 : 0.4} lineWidth={isSelected ? 2 : 1} />
      )}
    </group>
  );
}

/**
 * Satellite
 * Renders the CubeSat itself in the 3D scene.
 */
function Satellite({ setSatWorldPos }) {
  const isSimulating = useDashboardStore((s) => s.isSimulating);
  const groupRef = useRef();
  const orbitGroupRef = useRef();

  // White circular base orbit
  const baseRadius = 5.5;
  const basePoints = useMemo(() => {
    return Array.from({ length: 100 }).map((_, i) => {
      const angle = (i / 99) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(angle) * baseRadius, 0, Math.sin(angle) * baseRadius);
    });
  }, []);

  // Avoidance orbit path (white, shifted)
  const avoidanceRadius = 6.8;
  const avoidancePoints = useMemo(() => {
    return Array.from({ length: 100 }).map((_, i) => {
      const angle = (i / 99) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(angle) * avoidanceRadius, 0, Math.sin(angle) * avoidanceRadius);
    });
  }, []);

  useFrame((state) => {
    const time = state.clock.elapsedTime;

    // Tilt the orbit slightly for better 3D depth
    if (orbitGroupRef.current) {
      orbitGroupRef.current.rotation.x = 0.15;
      orbitGroupRef.current.rotation.z = 0.1;
    }

    if (groupRef.current) {
      const targetRadius = isSimulating ? avoidanceRadius : baseRadius;

      if (!groupRef.current.userData.currentRadius) {
        groupRef.current.userData.currentRadius = baseRadius;
      }
      groupRef.current.userData.currentRadius += (targetRadius - groupRef.current.userData.currentRadius) * 0.05;
      const r = groupRef.current.userData.currentRadius;

      // Revolution speed around Earth
      const angle = time * 0.4;
      groupRef.current.position.x = Math.cos(angle) * r;
      groupRef.current.position.z = Math.sin(angle) * r;
      groupRef.current.position.y = Math.sin(time * 2) * 0.05;

      // Ensure the satellite model faces its travel direction
      groupRef.current.rotation.y = -angle;

      if (isSimulating) {
        // Bank/tilt into the shifted orbit
        groupRef.current.rotation.z += (0.3 - groupRef.current.rotation.z) * 0.05;
      } else {
        groupRef.current.rotation.z += (0 - groupRef.current.rotation.z) * 0.05;
      }

      if (setSatWorldPos) {
        const pos = new THREE.Vector3();
        groupRef.current.getWorldPosition(pos);
        setSatWorldPos(pos);
      }
    }
  });

  return (
    <group ref={orbitGroupRef}>
      {/* Primary White Satellite Orbit */}
      <Line points={basePoints} color="white" lineWidth={1} transparent opacity={0.4} />

      {/* Changed Orbit when Avoidance active */}
      {isSimulating && (
        <Line points={avoidancePoints} color="white" lineWidth={2} transparent opacity={0.9} dashed />
      )}

      {/* Satellite Model */}
      <group ref={groupRef}>
        <mesh>
          <boxGeometry args={[0.3, 0.4, 0.3]} />
          <meshStandardMaterial color="#3b82f6" emissive="#1d4ed8" emissiveIntensity={0.5} metalness={0.8} />
        </mesh>
        <mesh position={[0.4, 0, 0]}>
          <boxGeometry args={[0.5, 0.02, 0.3]} />
          <meshStandardMaterial color="#1e3a8a" roughness={0.1} metalness={0.8} />
        </mesh>
        <mesh position={[-0.4, 0, 0]}>
          <boxGeometry args={[0.5, 0.02, 0.3]} />
          <meshStandardMaterial color="#1e3a8a" roughness={0.1} metalness={0.8} />
        </mesh>
        <mesh position={[0, -0.22, 0]}>
          <cylinderGeometry args={[0.05, 0.08, 0.05]} />
          <meshBasicMaterial color={isSimulating ? "#38bdf8" : "#fbbf24"} />
          {isSimulating && <pointLight color="#38bdf8" distance={2} intensity={2} />}
        </mesh>

        <Html distanceFactor={10}>
          <div className="px-1.5 py-1 rounded border border-blue-500/50 bg-blue-950/80 text-[8px] font-black text-white whitespace-nowrap shadow-lg translate-x-6 relative bottom-4">
            SENTINEL-1
            {isSimulating && <div className="text-[7px] text-green-400 mt-0.5 animate-pulse">AVOIDANCE THRUST</div>}
          </div>
        </Html>
      </group>
    </group>
  );
}

/**
 * Earth
 * Enhanced realistic Earth with atmosphere, ocean glow, and continent hints.
 */
function Earth({ setGsWorldPos }) {
  const meshRef = useRef();
  const gsRef = useRef();
  const atmosphereRef = useRef();

  // Ground station (Houston ~29.7N, 95.3W)
  const gsPos = useMemo(() => {
    const latRad = 0.52; // ~29.7 deg
    const lonRad = -1.66; // ~-95.3 deg
    const dist = 4.02;
    const x = dist * Math.cos(latRad) * Math.cos(lonRad);
    const y = dist * Math.sin(latRad);
    const z = dist * Math.cos(latRad) * Math.sin(lonRad);
    return new THREE.Vector3(x, y, z);
  }, []);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.0015;

      if (gsRef.current && setGsWorldPos) {
        const pos = new THREE.Vector3();
        gsRef.current.getWorldPosition(pos);
        setGsWorldPos(pos);
      }
    }
    // Atmosphere counter-rotation for depth effect
    if (atmosphereRef.current) {
      atmosphereRef.current.rotation.y -= 0.0003;
    }
  });

  return (
    <group ref={meshRef}>
      {/* Core Earth sphere — deep ocean blue with subtle green hints */}
      <mesh>
        <sphereGeometry args={[4, 128, 128]} />
        <meshPhongMaterial
          color="#0c2d6b"
          specular="#1e40af"
          shininess={15}
          emissive="#0a1e4a"
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* Continental landmass layer — slightly larger, partial opacity */}
      <mesh scale={[1.001, 1.001, 1.001]}>
        <sphereGeometry args={[4, 64, 64]} />
        <meshStandardMaterial
          color="#1a472a"
          transparent
          opacity={0.15}
          roughness={0.9}
          metalness={0}
        />
      </mesh>

      {/* Wireframe grid overlay — mission control aesthetic */}
      <mesh scale={[1.002, 1.002, 1.002]}>
        <sphereGeometry args={[4, 24, 24]} />
        <meshBasicMaterial color="#3b82f6" wireframe transparent opacity={0.06} />
      </mesh>

      {/* Inner atmosphere glow */}
      <mesh scale={[1.02, 1.02, 1.02]} ref={atmosphereRef}>
        <sphereGeometry args={[4, 48, 48]} />
        <meshBasicMaterial
          color="#60a5fa"
          transparent
          opacity={0.08}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Outer atmosphere halo */}
      <mesh scale={[1.08, 1.08, 1.08]}>
        <sphereGeometry args={[4, 32, 32]} />
        <meshBasicMaterial
          color="#3b82f6"
          transparent
          opacity={0.04}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Fresnel-like edge glow ring */}
      <mesh scale={[1.12, 1.12, 1.12]}>
        <sphereGeometry args={[4, 32, 32]} />
        <meshBasicMaterial
          color="#93c5fd"
          transparent
          opacity={0.02}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Polar ice cap highlights */}
      <mesh position={[0, 3.95, 0]} rotation={[0, 0, 0]}>
        <sphereGeometry args={[0.8, 16, 8, 0, Math.PI * 2, 0, 0.5]} />
        <meshBasicMaterial color="#e0f2fe" transparent opacity={0.12} />
      </mesh>
      <mesh position={[0, -3.95, 0]} rotation={[Math.PI, 0, 0]}>
        <sphereGeometry args={[0.6, 16, 8, 0, Math.PI * 2, 0, 0.5]} />
        <meshBasicMaterial color="#e0f2fe" transparent opacity={0.1} />
      </mesh>

      {/* Ground Station */}
      <group position={[gsPos.x, gsPos.y, gsPos.z]} ref={gsRef}>
        {/* Base */}
        <mesh>
          <cylinderGeometry args={[0.03, 0.1, 0.12]} />
          <meshStandardMaterial color="#22c55e" emissive="#4ade80" emissiveIntensity={1.2} />
        </mesh>
        {/* Antenna dish */}
        <mesh position={[0, 0.1, 0]}>
          <sphereGeometry args={[0.04, 8, 8]} />
          <meshBasicMaterial color="#86efac" />
        </mesh>
        {/* Beacon glow */}
        <pointLight color="#22c55e" distance={1.5} intensity={0.5} position={[0, 0.15, 0]} />
        <Html distanceFactor={15}>
          <div className="px-1.5 py-0.5 rounded bg-green-950/90 border border-green-500/40 text-[6px] font-black text-green-400 whitespace-nowrap shadow-lg shadow-green-900/30 translate-x-3 -translate-y-3">
            📡 HOUSTON-GS
          </div>
        </Html>
      </group>
    </group>
  );

}

/**
 * CommLink
 * Draws a communication line if satellite is above horizon of the ground station.
 */
function CommLink({ satPos, gsPos }) {
  const isActive = satPos && gsPos && satPos.distanceTo(gsPos) < 10.0;

  if (!isActive) return null;

  return (
    <group>
      <Line points={[gsPos, satPos]} color="#22c55e" lineWidth={2} transparent opacity={0.6} dashed dashScale={10} dashSize={0.5} dashRatio={0.5} />
      <Html position={gsPos.clone().lerp(satPos, 0.5)}>
        <div className="text-[7px] text-green-400 font-bold bg-black/60 px-1 rounded transform -translate-x-1/2 -translate-y-1/2">
          DOWNLINK ACTIVE
        </div>
      </Html>
    </group>
  );
}

/**
 * OrbitalView (3D Version)
 */
function OrbitalView() {
  const tracks = useDashboardStore((s) => s.tracks);
  const [satPos, setSatPos] = useState(null);
  const [gsPos, setGsPos] = useState(null);

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
            autoRotate={false}
          />

          {/* Sunlight — main directional light */}
          <ambientLight intensity={0.3} color="#b0c4de" />
          <directionalLight position={[15, 10, 10]} intensity={2.0} color="#fffaf0" castShadow />
          <pointLight position={[-10, -5, -10]} intensity={0.4} color="#1e40af" />
          <pointLight position={[0, 8, 0]} intensity={0.3} color="#60a5fa" />

          <Stars radius={100} depth={50} count={7000} factor={4} saturation={0} fade speed={1} />

          <Suspense fallback={null}>
            <Earth setGsWorldPos={setGsPos} />
            <Satellite setSatWorldPos={setSatPos} />
            <CommLink satPos={satPos} gsPos={gsPos} />
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
