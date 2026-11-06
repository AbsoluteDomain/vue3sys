<template>
  <el-dialog
    v-model="visible"
    title="URDF 模型展示"
    width="1040px"
    top="5vh"
    destroy-on-close
    class="urdf-dialog"
    @opened="handleOpened"
    @closed="handleClosed"
  >
    <div class="urdf-toolbar">
      <el-radio-group v-model="currentModelKey" size="small" @change="handleModelChange">
        <el-radio-button v-for="item in urdfModels" :key="item.key" :value="item.key">
          {{ item.label }}
        </el-radio-button>
      </el-radio-group>
      <div class="urdf-toolbar-right">
        <el-switch
          v-model="showFrames"
          size="small"
          active-text="显示坐标系"
          @change="handleFramesChange"
        />
        <el-button size="small" @click="resetView">重置视角</el-button>
      </div>
    </div>

    <div class="urdf-body">
      <div ref="viewportRef" class="urdf-viewport" v-loading="loading" element-loading-text="模型加载中...">
        <div v-if="selectedLinkName" class="urdf-selected">已选中：{{ selectedLinkName }}</div>
        <el-empty v-if="loadError" class="urdf-empty" description="模型加载失败，请检查 URDF 资源是否完整" />
      </div>

      <div v-if="joints.length" class="urdf-joints">
        <div class="urdf-joints-head">
          <span class="urdf-joints-title">关节控制</span>
          <el-radio-group v-model="jointUnit" size="small">
            <el-radio-button value="rad">弧度</el-radio-button>
            <el-radio-button value="deg">角度</el-radio-button>
          </el-radio-group>
        </div>
        <div v-for="joint in joints" :key="joint.name" class="urdf-joint-item">
          <div class="urdf-joint-head">
            <span class="urdf-joint-name">{{ joint.name }}</span>
            <el-input-number
              class="urdf-joint-input"
              :model-value="jointDisplayValue(joint)"
              :min="jointDisplayLimit(joint, joint.min)"
              :max="jointDisplayLimit(joint, joint.max)"
              :step="jointStep(joint)"
              :precision="2"
              :controls="false"
              size="small"
              @change="(value) => handleJointChange(joint, value)"
            />
          </div>
          <el-slider
            :model-value="jointDisplayValue(joint)"
            :min="jointDisplayLimit(joint, joint.min)"
            :max="jointDisplayLimit(joint, joint.max)"
            :step="jointStep(joint)"
            :show-tooltip="false"
            size="small"
            @input="(value) => handleJointChange(joint, value)"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <span class="urdf-tip">左键旋转 · 滚轮缩放 · 右键平移 · 单击部件选中高亮</span>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import * as THREE from 'three'
import URDFLoader from 'urdf-loader'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// 可选模型列表：新增模型时，把 urdf 放到 public/urdf/<目录>/ 下并在此登记即可
const urdfModels = [
  { key: 'TCB610', label: 'TCB610', file: 'TCB610/fdr2.urdf' },
  { key: 'TCB710', label: 'TCB710', file: 'TCB710/fdr2.urdf' }
]
// URDF 中 package://fdr2/meshes/xxx.STL 对应的资源目录
const packageDir = 'fdr2'
// 可拖动的关节类型
const movableJointTypes = ['revolute', 'continuous', 'prismatic']

const visible = ref(false)
const loading = ref(false)
const loadError = ref(false)
const currentModelKey = ref(urdfModels[0].key)
const viewportRef = ref(null)
const joints = ref([])
const selectedLinkName = ref('')
const showFrames = ref(true)
const jointUnit = ref('rad')

let renderer = null
let scene = null
let camera = null
let controls = null
let resizeObserver = null
let currentRobot = null
let highlightedMeshes = []
let frameHelpers = []
let raycaster = null
let pointerStart = null
let frameId = 0
let loadToken = 0

const baseUrl = () => (import.meta.env.BASE_URL || '/').replace(/\/?$/, '/')

const resolveUrl = (path) => `${baseUrl()}urdf/${path}`

const disposeObject = (object) => {
  object.traverse((child) => {
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material]
      materials.forEach((material) => {
        Object.keys(material).forEach((key) => {
          const value = material[key]
          if (value && value.isTexture) value.dispose()
        })
        material.dispose()
      })
    }
  })
}

const findUrdfLink = (object) => {
  let current = object
  while (current) {
    if (current.isURDFLink) return current
    current = current.parent
  }
  return null
}

// 取主题主色作为涂色高亮色，保证与 Element Plus 主题一致
const getHighlightColor = () => {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue('--el-color-primary')
    .trim()
  return value || '#409eff'
}

const paintMaterial = (material, color) => {
  // 克隆材质后再改色，避免污染 URDF 中共享的材质（同一材质可能被多个部件复用）
  const cloned = material.clone()
  if (cloned.color) cloned.color.set(color)
  return cloned
}

const restoreHighlight = () => {
  highlightedMeshes.forEach(({ mesh, original, cloned }) => {
    mesh.material = original
    const clonedMaterials = Array.isArray(cloned) ? cloned : [cloned]
    clonedMaterials.forEach((material) => material?.dispose())
  })
  highlightedMeshes = []
}

const clearSelection = () => {
  selectedLinkName.value = ''
  restoreHighlight()
}

const highlightLink = (link) => {
  restoreHighlight()
  if (!link) {
    selectedLinkName.value = ''
    return
  }

  const color = getHighlightColor()
  link.traverse((child) => {
    // 只涂该 link 自身的可视网格，子 link 的部件保持原色
    if (!child.isMesh || !child.material || findUrdfLink(child) !== link) return
    const original = child.material
    const cloned = Array.isArray(original)
      ? original.map((material) => paintMaterial(material, color))
      : paintMaterial(original, color)
    child.material = cloned
    highlightedMeshes.push({ mesh: child, original, cloned })
  })

  const linkName = link.urdfName || link.name || '未知部件'
  // joint 的可视部位属于其子 link，选中时同时给出驱动的关节名，便于对应 joint1/joint2
  const jointName = link.parent?.isURDFJoint ? link.parent.name : ''
  selectedLinkName.value = jointName ? `${linkName}（${jointName}）` : linkName
}

/**
 * 为每个 link 挂一个坐标轴显示（RGB 分别为 X/Y/Z 轴），跟随 link 一起运动
 */
const buildFrameHelpers = (robot) => {
  frameHelpers = []
  if (!robot) return
  const box = computeRobotBox(robot)
  const diagonal = box.isEmpty() ? 1 : box.getSize(new THREE.Vector3()).length()
  // 坐标轴长度按模型整体尺寸自适应，保证在视口里清晰可见
  const size = Math.max(diagonal * 0.12, 0.01)

  Object.values(robot.links || {}).forEach((link) => {
    const helper = new THREE.AxesHelper(size)
    // AxesHelper 默认是渐变配色（如红→橙），这里改成纯 RGB 红/绿/蓝：255,0,0 / 0,255,0 / 0,0,255
    helper.setColors(0xff0000, 0x00ff00, 0x0000ff)
    helper.userData.isFrameHelper = true
    // 坐标系只作参考显示，不参与射线拾取
    helper.raycast = () => {}
    helper.visible = showFrames.value
    link.add(helper)
    frameHelpers.push(helper)
  })
}

const handleFramesChange = (value) => {
  frameHelpers.forEach((helper) => {
    helper.visible = !!value
  })
}

const pickLink = (event) => {
  if (!currentRobot || !camera || !renderer) return
  const rect = renderer.domElement.getBoundingClientRect()
  const pointer = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  )
  if (!raycaster) raycaster = new THREE.Raycaster()
  raycaster.setFromCamera(pointer, camera)
  const hits = raycaster.intersectObject(currentRobot, true)
  const hit = hits.find((item) => item.object.isMesh)
  const link = hit ? findUrdfLink(hit.object) : null
  highlightLink(link)
}

const animate = () => {
  frameId = requestAnimationFrame(animate)
  controls?.update()
  if (renderer && scene && camera) renderer.render(scene, camera)
}

const resize = () => {
  const el = viewportRef.value
  if (!el || !renderer || !camera) return
  const width = el.clientWidth
  const height = el.clientHeight
  if (!width || !height) return
  renderer.setSize(width, height)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

const initScene = () => {
  const el = viewportRef.value
  if (!el || renderer) return

  const width = el.clientWidth || 900
  const height = el.clientHeight || 560

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(width, height)
  const canvas = renderer.domElement
  canvas.style.touchAction = 'none'
  canvas.style.userSelect = 'none'
  canvas.style.cursor = 'grab'
  el.appendChild(canvas)

  // 阻止滚轮缩放时把页面一起滚动，以及右键平移弹出浏览器菜单
  canvas.addEventListener('wheel', (event) => event.preventDefault(), { passive: false })
  canvas.addEventListener('contextmenu', (event) => event.preventDefault())
  canvas.addEventListener('pointerdown', (event) => {
    pointerStart = { x: event.clientX, y: event.clientY }
    // 阻止鼠标中键触发浏览器的自动滚动
    if (event.button === 1) event.preventDefault()
  })
  canvas.addEventListener('click', (event) => {
    // 拖动旋转时不触发选中，只有单击才拾取部件
    const distance = pointerStart ? Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) : 0
    pointerStart = null
    if (distance < 5) pickLink(event)
  })
  canvas.addEventListener('pointerleave', () => {
    pointerStart = null
  })

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100)
  camera.position.set(1.2, 0.9, 1.2)

  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x555555, 1.6)
  scene.add(hemiLight)
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.4)
  dirLight.position.set(1.5, 2.5, 2)
  scene.add(dirLight)
  const backLight = new THREE.DirectionalLight(0xffffff, 0.6)
  backLight.position.set(-2, -1, -1.5)
  scene.add(backLight)

  const grid = new THREE.GridHelper(2, 20, 0x999999, 0xdddddd)
  grid.material.transparent = true
  grid.material.opacity = 0.35
  scene.add(grid)

  controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 0.05
  controls.maxDistance = 20
  controls.target.set(0, 0.3, 0)

  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(el)
  window.addEventListener('resize', resize)

  animate()
}

// 计算模型（不含坐标系辅助对象）的世界包围盒
const computeRobotBox = (robot) => {
  const box = new THREE.Box3()
  const tempBox = new THREE.Box3()
  robot.updateWorldMatrix(true, true)
  robot.traverse((child) => {
    if (child.userData?.isFrameHelper || !child.isMesh || !child.geometry) return
    if (!child.geometry.boundingBox) child.geometry.computeBoundingBox()
    if (!child.geometry.boundingBox) return
    tempBox.copy(child.geometry.boundingBox).applyMatrix4(child.matrixWorld)
    box.union(tempBox)
  })
  return box
}

const resetView = () => {
  if (!currentRobot || !camera || !controls) return
  const box = computeRobotBox(currentRobot)
  if (box.isEmpty()) return

  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const radius = Math.max(size.x, size.y, size.z, 0.1) / 2
  const distance = (radius / Math.sin((camera.fov * Math.PI) / 360)) * 2.2

  camera.position.copy(center).add(new THREE.Vector3(1, 0.75, 1).normalize().multiplyScalar(distance))
  camera.near = Math.max(distance / 1000, 0.001)
  camera.far = distance * 10
  camera.updateProjectionMatrix()

  controls.target.copy(center)
  controls.minDistance = radius * 0.3
  controls.maxDistance = distance * 4
  controls.update()
}

const buildJointControls = (robot) => {
  joints.value = Object.values(robot.joints || {})
    .filter((joint) => movableJointTypes.includes(joint.jointType))
    .map((joint) => {
      const continuous = joint.jointType === 'continuous'
      const lower = continuous ? -Math.PI : joint.limit?.lower ?? -Math.PI
      const upper = continuous ? Math.PI : joint.limit?.upper ?? Math.PI
      return {
        name: joint.name,
        type: joint.jointType,
        min: Number.isFinite(lower) ? lower : -Math.PI,
        max: Number.isFinite(upper) ? upper : Math.PI,
        // URDF 连续关节的 lower/upper 为 0，需用 ±π 作为拖动范围
        value: 0
      }
    })
}

// 角度/弧度显示单位，joint.value 内部始终保存弧度
const isAngularJoint = (joint) => joint.type === 'revolute' || joint.type === 'continuous'

const jointDisplayValue = (joint) => {
  if (!isAngularJoint(joint) || jointUnit.value !== 'deg') return joint.value
  return (joint.value * 180) / Math.PI
}

const jointDisplayLimit = (joint, limit) => {
  if (!isAngularJoint(joint) || jointUnit.value !== 'deg') return limit
  return Math.round(((limit * 180) / Math.PI) * 100) / 100
}

const jointStep = (joint) => (isAngularJoint(joint) && jointUnit.value === 'deg' ? 1 : 0.01)

const handleJointChange = (joint, value) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return
  // 角度模式下输入框/滑块给出的是角度，需换算回弧度后再驱动模型
  const radian = isAngularJoint(joint) && jointUnit.value === 'deg' ? (value * Math.PI) / 180 : value
  joint.value = radian
  currentRobot?.setJointValue(joint.name, radian)
}

const loadModel = (modelKey) => {
  if (!scene) return
  const model = urdfModels.find((item) => item.key === modelKey) || urdfModels[0]
  const token = ++loadToken

  loading.value = true
  loadError.value = false
  clearSelection()
  joints.value = []
  frameHelpers = []

  if (currentRobot) {
    scene.remove(currentRobot)
    disposeObject(currentRobot)
    currentRobot = null
  }

  const manager = new THREE.LoadingManager()
  manager.onLoad = () => {
    if (token === loadToken) {
      loading.value = false
      // 等所有网格加载完成后再建坐标系，才能算出准确的模型尺寸
      buildFrameHelpers(currentRobot)
      resetView()
    }
  }
  manager.onError = () => {
    if (token === loadToken) {
      loading.value = false
      loadError.value = true
    }
  }

  const loader = new URDFLoader(manager)
  loader.packages = { fdr2: `${baseUrl()}urdf/${packageDir}` }
  loader.load(
    resolveUrl(model.file),
    (robot) => {
      if (token !== loadToken) {
        disposeObject(robot)
        return
      }
      // URDF 为 Z 轴朝上，Three.js 为 Y 轴朝上，整体旋转后模型才能立起来
      robot.rotation.x = -Math.PI / 2
      scene.add(robot)
      currentRobot = robot
      buildJointControls(robot)
    },
    undefined,
    (error) => {
      if (token !== loadToken) return
      console.error(error)
      loading.value = false
      loadError.value = true
    }
  )
}

const handleOpened = () => {
  nextTick(() => {
    initScene()
    loadModel(currentModelKey.value)
  })
}

const handleModelChange = (value) => {
  loadModel(value)
}

const cleanup = () => {
  loadToken += 1
  cancelAnimationFrame(frameId)
  frameId = 0

  resizeObserver?.disconnect()
  resizeObserver = null
  window.removeEventListener('resize', resize)

  clearSelection()

  if (currentRobot) {
    disposeObject(currentRobot)
    currentRobot = null
  }

  controls?.dispose()
  controls = null

  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
    renderer = null
  }

  raycaster = null
  pointerStart = null
  joints.value = []
  frameHelpers = []
  scene = null
  camera = null
  loading.value = false
  loadError.value = false
}

const handleClosed = () => {
  cleanup()
}

const open = (modelKey) => {
  if (modelKey && urdfModels.some((item) => item.key === modelKey)) {
    currentModelKey.value = modelKey
  }
  visible.value = true
}

defineExpose({ open })
</script>

<style scoped>
.urdf-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.urdf-toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.urdf-body {
  display: flex;
  gap: 12px;
}

.urdf-viewport {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 560px;
  overflow: hidden;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  user-select: none;
}

.urdf-viewport :deep(canvas) {
  display: block;
}

.urdf-selected {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  padding: 2px 8px;
  font-size: 12px;
  color: var(--el-text-color-primary);
  pointer-events: none;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 4px;
}

.urdf-empty {
  position: absolute;
  inset: 0;
}

.urdf-joints {
  width: 220px;
  height: 560px;
  padding: 8px 12px;
  overflow-y: auto;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.urdf-joints-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.urdf-joints-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.urdf-joint-item {
  margin-bottom: 4px;
}

.urdf-joint-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.urdf-joint-input {
  width: 88px;
}

.urdf-joint-input :deep(.el-input__inner) {
  text-align: right;
}

.urdf-tip {
  margin-right: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
