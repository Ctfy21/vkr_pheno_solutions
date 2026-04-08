export interface Organization {
  id: string
  name: string
  description: string
  members: User[]
  createdAt: string
}

export interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'researcher' | 'observer'
  organizationId: string
  avatarUrl?: string
}

export interface Program {
  id: string
  name: string
  abbreviation: string
  objective: string
  crop: string
  leadPerson: string
  organizationId: string
  trials: Trial[]
}

export interface Trial {
  id: string
  name: string
  description: string
  programId: string
  startDate: string
  endDate: string
  active: boolean
  studies: Study[]
}

export interface Study {
  id: string
  name: string
  description: string
  studyType: string
  trialId: string
  startDate: string
  endDate: string
  locationId: string
  climateChamber?: ClimateChamber
  observationVariables: ObservationVariable[]
  plantCount: number
  status: 'draft' | 'active' | 'completed' | 'archived'
}

export interface Location {
  id: string
  name: string
  locationType: string
  coordinates: { lat: number; lng: number }
  instituteName: string
}

export interface Germplasm {
  id: string
  germplasmName: string
  genus: string
  species: string
  accessionNumber: string
  pedigree: string
  instituteCode: string
}

export interface Trait {
  id: string
  traitName: string
  traitDescription: string
  traitClass: 'morphological' | 'physiological' | 'biochemical' | 'phenological' | 'agronomic'
  entity: string
  attribute: string
  coTermId: string
}

export interface Method {
  id: string
  methodName: string
  methodClass: 'measurement' | 'counting' | 'estimation' | 'computation' | 'observation'
  description: string
  formula?: string
  reference?: string
}

export interface Scale {
  id: string
  scaleName: string
  dataType: 'numerical' | 'ordinal' | 'nominal' | 'date' | 'text'
  units?: string
  decimalPlaces?: number
  validValues?: string[]
}

export interface ObservationVariable {
  id: string
  name: string
  trait: Trait
  method: Method
  scale: Scale
  coTermId: string
}

export interface ObservationUnit {
  id: string
  name: string
  studyId: string
  germplasm: Germplasm
  position: string
  treatment?: string
  observations: Observation[]
  images: PlantImage[]
}

export interface Observation {
  id: string
  observationUnitId: string
  variableId: string
  variableName: string
  value: string
  observationTimeStamp: string
  collector: string
}

export interface PlantImage {
  id: string
  fileName: string
  mimeType: string
  width: number
  height: number
  observationUnitId: string
  url: string
  processedUrl?: string
  detections?: number
}

export interface ClimateChamber {
  id: string
  name: string
  organizationId: string
  locationId: string
  sensors: Sensor[]
}

export interface Sensor {
  id: string
  name: string
  type: 'temperature' | 'humidity' | 'light' | 'co2'
  unit: string
}

export interface SensorReading {
  sensorId: string
  value: number
  timestamp: string
}

export interface ContainerImage {
  id: string
  name: string
  tag: string
  sha256: string
  description: string
  createdAt: string
}
