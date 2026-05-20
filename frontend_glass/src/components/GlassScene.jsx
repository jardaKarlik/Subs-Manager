import { useRef, useEffect, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Lightformer, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

/**
 * Glass Material Shader for physically-based glass effect
 * Based on KHR_materials_transmission and dispersion
 */
function GlassMaterial() {
  const material = useRef()

  useEffect(() => {
    if (material.current) {
      material.current.transmission = 1.0
      material.current.roughness = 0.41
      material.current.thickness = 1.35
      material.current.ior = 2.14
      material.current.chromaticAberration = 0.415
      material.current.clearcoat = 1.0
      material.current.clearcoatRoughness = 0.59
    }
  }, [])

  return material
}

/**
 * 3D Glass Pane Component
 * Renders a single glass pane with physical properties
 */
function GlassPaneModel({ position, rotation, scale }) {
  const groupRef = useRef()
  const [mouseX, setMouseX] = useState(0)
  const [mouseY, setMouseY] = useState(0)

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMouseX((e.clientX / window.innerWidth) * 2 - 1)
      setMouseY(-(e.clientY / window.innerHeight) * 2 + 1)
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  useFrame(() => {
    if (groupRef.current) {
      // Parallax effect: 1.9 strength
      groupRef.current.position.x += (mouseX * 2 - groupRef.current.position.x) * 0.05
      groupRef.current.position.y += (mouseY * 2 - groupRef.current.position.y) * 0.05

      // Gentle rotation
      groupRef.current.rotation.x += 0.0002
      groupRef.current.rotation.y += 0.0003
    }
  })

  return (
    <group ref={groupRef} position={position} rotation={rotation} scale={scale}>
      <mesh>
        <boxGeometry args={[1, 1, 0.1]} />
        <meshPhysicalMaterial
          transmission={1.0}
          roughness={0.41}
          metalness={0}
          thickness={1.35}
          ior={2.14}
          chromaticAberration={0.415}
          clearcoat={1}
          clearcoatRoughness={0.59}
          iridescence={1}
          iridescenceIOR={2.34}
          attenuationDistance={4.7}
          attenuationColor={new THREE.Color(1, 1, 1)}
        />
      </mesh>
    </group>
  )
}

/**
 * Main 3D Scene Component
 * Renders the glass effect environment
 */
function GlassScene() {
  const { camera } = useThree()

  useEffect(() => {
    camera.position.z = 3
  }, [camera])

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, -10, 10]} intensity={0.4} />

      {/* Environment */}
      <Environment preset="night" />

      {/* Glass Panes Grid */}
      <group position={[0, 0, 0]}>
        {/* 5 glass panes in a grid-like formation */}
        <GlassPaneModel position={[-1, 1, 0]} rotation={[0.1, 0.1, 0]} scale={0.8} />
        <GlassPaneModel position={[0, 1, -0.2]} rotation={[0, 0.2, 0.1]} scale={0.9} />
        <GlassPaneModel position={[1, 1, 0]} rotation={[-0.1, 0.1, 0]} scale={0.8} />
        <GlassPaneModel position={[-0.5, -0.5, -0.1]} rotation={[0.2, -0.1, 0]} scale={0.85} />
        <GlassPaneModel position={[0.5, -0.5, 0.1]} rotation={[-0.1, -0.2, 0.1]} scale={0.85} />
      </group>

      {/* Post-processing */}
      <EffectComposer>
        <Bloom
          luminanceThreshold={1.1}
          luminanceSmoothing={0.9}
          height={300}
          intensity={0.05}
          radius={1.8}
        />
      </EffectComposer>
    </>
  )
}

/**
 * Canvas Wrapper for Glass Effect
 * Used as an optional floating enhancement above the dashboard
 */
export function GlassEffectCanvas({ className = '' }) {
  return (
    <Canvas className={className}>
      <GlassScene />
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.3} />
    </Canvas>
  )
}

export default GlassMaterial
