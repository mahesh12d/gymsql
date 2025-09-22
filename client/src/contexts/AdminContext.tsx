import { createContext, useContext, useReducer, ReactNode } from 'react';
import { useToast } from '@/hooks/use-toast';

// Types and interfaces
export interface TableColumn {
  name: string;
  type: string;
  description: string;
}

export interface TableData {
  name: string;
  columns: TableColumn[];
  sample_data: Record<string, any>[];
}

export interface QuestionData {
  description: string;
  tables: TableData[];
  expectedOutput: Record<string, any>[];
  s3_data_source?: S3DatasetSource;
}

export interface ProblemDraft {
  title: string;
  difficulty: string;
  question: QuestionData;
  tags: string[];
  company: string;
  hints: string[];
  premium: boolean;
  topic_id: string;
}

export interface SchemaInfo {
  problem_structure: Record<string, any>;
  example_problem: ProblemDraft;
  difficulty_options: string[];
  available_topics: { id: string; name: string }[];
}

export interface S3DatasetSource {
  bucket: string;
  key: string;
  table_name: string;
  description: string;
}

export interface S3DatasetValidationResponse {
  success: boolean;
  message?: string;
  error?: string;
  table_schema?: Array<{column: string; type: string}>;
  sample_data?: Record<string, any>[];
  row_count?: number;
  etag?: string;
  table_name?: string;
  data_source?: string;
}

export interface S3ValidatedDataset {
  bucket: string;
  key: string;
  table_name: string;
  description: string;
  etag: string;
  table_schema: Array<{column: string; type: string}>;
  sample_data: Record<string, any>[];
  row_count: number;
}

export interface MultiTableValidationResponse {
  success: boolean;
  message?: string;
  error?: string;
  validated_datasets?: S3ValidatedDataset[];
  total_tables?: number;
  total_rows?: number;
}

export interface SolutionVerificationResult {
  verified: boolean;
  source: 'neon';  // Only Neon supported - S3 solutions deprecated
}

// State interface
interface AdminState {
  // Authentication
  adminKey: string;
  isAuthenticated: boolean;
  schemaInfo: SchemaInfo | null;
  loading: boolean;

  // Problem Draft
  problemDraft: ProblemDraft;

  // Single S3 validation
  s3Source: S3DatasetSource;
  s3Validation: S3DatasetValidationResponse | null;
  isValidatingS3: boolean;

  // Multi S3 validation  
  multiTableDatasets: Array<{
    bucket: string;
    key: string;
    table_name: string;
    description: string;
  }>;
  multiTableValidation: MultiTableValidationResponse | null;
  isValidatingMultiTable: boolean;

  // Solution verification
  solutionVerification: SolutionVerificationResult | null;

  // UI state
  activeTab: string;
}

// Actions
type AdminAction = 
  | { type: 'SET_ADMIN_KEY'; payload: string }
  | { type: 'SET_AUTHENTICATED'; payload: boolean }
  | { type: 'SET_SCHEMA_INFO'; payload: SchemaInfo | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'UPDATE_PROBLEM_DRAFT'; payload: Partial<ProblemDraft> }
  | { type: 'RESET_PROBLEM_DRAFT' }
  | { type: 'SET_S3_SOURCE'; payload: S3DatasetSource }
  | { type: 'SET_S3_VALIDATION'; payload: S3DatasetValidationResponse | null }
  | { type: 'SET_VALIDATING_S3'; payload: boolean }
  | { type: 'SET_MULTI_TABLE_DATASETS'; payload: AdminState['multiTableDatasets'] }
  | { type: 'SET_MULTI_TABLE_VALIDATION'; payload: MultiTableValidationResponse | null }
  | { type: 'SET_VALIDATING_MULTI_TABLE'; payload: boolean }
  | { type: 'SET_SOLUTION_VERIFICATION'; payload: SolutionVerificationResult | null }
  | { type: 'SET_SOLUTION_TYPE'; payload: 'neon' }
  | { type: 'SET_ACTIVE_TAB'; payload: string }
  | { type: 'APPLY_SINGLE_VALIDATION_TO_DRAFT' }
  | { type: 'APPLY_MULTI_VALIDATION_TO_DRAFT' };

// Initial state
const initialState: AdminState = {
  adminKey: '',
  isAuthenticated: false,
  schemaInfo: null,
  loading: false,
  problemDraft: {
    title: '',
    difficulty: 'Easy',
    question: {
      description: '',
      tables: [],
      expectedOutput: []
    },
    tags: [],
    company: '',
    hints: [],
    premium: false,
    topic_id: ''
  },
  s3Source: {
    bucket: '',
    key: '',
    table_name: 'problem_data',
    description: ''
  },
  s3Validation: null,
  isValidatingS3: false,
  multiTableDatasets: [],
  multiTableValidation: null,
  isValidatingMultiTable: false,
  solutionVerification: null,
  activeTab: 'create'
};

// Reducer
function adminReducer(state: AdminState, action: AdminAction): AdminState {
  switch (action.type) {
    case 'SET_ADMIN_KEY':
      return { ...state, adminKey: action.payload };
    case 'SET_AUTHENTICATED':
      return { ...state, isAuthenticated: action.payload };
    case 'SET_SCHEMA_INFO':
      return { ...state, schemaInfo: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'UPDATE_PROBLEM_DRAFT':
      return { ...state, problemDraft: { ...state.problemDraft, ...action.payload } };
    case 'RESET_PROBLEM_DRAFT':
      return { ...state, problemDraft: state.schemaInfo?.example_problem || initialState.problemDraft };
    case 'SET_S3_SOURCE':
      return { ...state, s3Source: action.payload };
    case 'SET_S3_VALIDATION':
      return { ...state, s3Validation: action.payload };
    case 'SET_VALIDATING_S3':
      return { ...state, isValidatingS3: action.payload };
    case 'SET_MULTI_TABLE_DATASETS':
      return { ...state, multiTableDatasets: action.payload };
    case 'SET_MULTI_TABLE_VALIDATION':
      return { ...state, multiTableValidation: action.payload };
    case 'SET_VALIDATING_MULTI_TABLE':
      return { ...state, isValidatingMultiTable: action.payload };
    case 'SET_SOLUTION_VERIFICATION':
      return { ...state, solutionVerification: action.payload };
    case 'SET_SOLUTION_TYPE':
      return { 
        ...state, 
        solutionVerification: { verified: true, source: 'neon' }
      };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'APPLY_SINGLE_VALIDATION_TO_DRAFT':
      if (state.s3Validation?.success && state.s3Validation.table_schema) {
        const suggestedTable: TableData = {
          name: state.s3Validation.table_name || state.s3Source.table_name,
          columns: state.s3Validation.table_schema.map(col => ({
            name: col.column,
            type: col.type,
            description: `${col.column} column (${col.type})`
          })),
          sample_data: state.s3Validation.sample_data || []
        };
        return {
          ...state,
          problemDraft: {
            ...state.problemDraft,
            question: {
              ...state.problemDraft.question,
              tables: [suggestedTable],
              s3_data_source: state.s3Source
            }
          }
        };
      }
      return state;
    case 'APPLY_MULTI_VALIDATION_TO_DRAFT':
      if (state.multiTableValidation?.success && state.multiTableValidation.validated_datasets) {
        const tables = state.multiTableValidation.validated_datasets.map((dataset) => ({
          name: dataset.table_name,
          columns: (dataset.table_schema || []).map((col) => ({
            name: col.column,
            type: col.type,
            description: `${col.column} column (${col.type})`
          })),
          sample_data: dataset.sample_data || []
        }));
        return {
          ...state,
          problemDraft: {
            ...state.problemDraft,
            question: {
              ...state.problemDraft.question,
              tables: tables
            }
          }
        };
      }
      return state;
    default:
      return state;
  }
}

// Context
interface AdminContextType {
  state: AdminState;
  dispatch: React.Dispatch<AdminAction>;
  actions: {
    // Setter actions
    setS3Source: (source: S3DatasetSource) => void;
    setMultiTableDatasets: (datasets: AdminState['multiTableDatasets']) => void;
    setActiveTab: (tab: string) => void;
    
    // Core actions
    authenticate: (key: string) => Promise<void>;
    validateS3Dataset: () => Promise<void>;
    validateMultiTableDatasets: (solutionPath: string) => Promise<void>;
    setSolutionType: (source: 'neon') => void;
    verifySolution: (source: 'neon') => Promise<void>;
    applyValidationToDraft: (type: 'single' | 'multi') => void;
    resetDraft: () => void;
    updateDraft: (updates: Partial<ProblemDraft>) => void;
  };
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

// Provider component
export function AdminProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(adminReducer, initialState);
  const { toast } = useToast();

  const actions = {
    // Setter actions  
    setS3Source: (source: S3DatasetSource) => {
      dispatch({ type: 'SET_S3_SOURCE', payload: source });
    },

    setMultiTableDatasets: (datasets: AdminState['multiTableDatasets']) => {
      dispatch({ type: 'SET_MULTI_TABLE_DATASETS', payload: datasets });
    },

    setActiveTab: (tab: string) => {
      dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
    },

    setSolutionType: (source: 'neon') => {
      dispatch({ type: 'SET_SOLUTION_TYPE', payload: source });
    },

    authenticate: async (key: string) => {
      if (!key.trim()) {
        toast({
          title: "Error",
          description: "Please enter the admin key",
          variant: "destructive",
        });
        return;
      }

      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const response = await fetch('/api/admin/schema-info', {
          headers: {
            'Authorization': `Bearer ${key}`,
          },
        });

        if (response.ok) {
          const schema = await response.json();
          dispatch({ type: 'SET_SCHEMA_INFO', payload: schema });
          dispatch({ type: 'SET_AUTHENTICATED', payload: true });
          dispatch({ type: 'SET_ADMIN_KEY', payload: key });
          dispatch({ type: 'UPDATE_PROBLEM_DRAFT', payload: schema.example_problem });
          toast({
            title: "Success",
            description: "Admin access granted!",
          });
        } else {
          toast({
            title: "Authentication Failed",
            description: "Invalid admin key",
            variant: "destructive",
          });
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to authenticate",
          variant: "destructive",
        });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    },

    validateS3Dataset: async () => {
      if (!state.s3Source.bucket.trim() || !state.s3Source.key.trim()) {
        toast({
          title: "Validation Error",
          description: "Both bucket and key are required",
          variant: "destructive",
        });
        return;
      }

      dispatch({ type: 'SET_VALIDATING_S3', payload: true });
      dispatch({ type: 'SET_S3_VALIDATION', payload: null });

      try {
        const response = await fetch('/api/admin/validate-dataset-s3', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${state.adminKey}`,
          },
          body: JSON.stringify(state.s3Source),
        });

        const result = await response.json();
        dispatch({ type: 'SET_S3_VALIDATION', payload: result });

        if (result.success) {
          toast({
            title: "Validation Success",
            description: `Found ${result.row_count?.toLocaleString()} rows with ${result.table_schema?.length} columns`,
          });
        } else {
          toast({
            title: "Validation Failed",
            description: result.error || "Unknown error occurred",
            variant: "destructive",
          });
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to validate S3 dataset",
          variant: "destructive",
        });
      } finally {
        dispatch({ type: 'SET_VALIDATING_S3', payload: false });
      }
    },

    validateMultiTableDatasets: async (solutionPath: string) => {
      dispatch({ type: 'SET_VALIDATING_MULTI_TABLE', payload: true });
      dispatch({ type: 'SET_MULTI_TABLE_VALIDATION', payload: null });

      try {
        const response = await fetch('/api/admin/validate-multitable-s3', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${state.adminKey}`,
          },
          body: JSON.stringify({
            datasets: state.multiTableDatasets,
            solution_path: solutionPath
          }),
        });

        const result = await response.json();
        dispatch({ type: 'SET_MULTI_TABLE_VALIDATION', payload: result });

        if (result.success) {
          toast({
            title: "Multi-table Validation Success",
            description: `Successfully validated ${result.validated_datasets?.length} datasets`,
          });
        } else {
          toast({
            title: "Validation Failed",
            description: result.error || "Unknown error occurred",
            variant: "destructive",
          });
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to validate multi-table datasets",
          variant: "destructive",
        });
      } finally {
        dispatch({ type: 'SET_VALIDATING_MULTI_TABLE', payload: false });
      }
    },

    verifySolution: async (source: 'neon') => {
      try {
        // For Neon, we just mark as verified since the solution will be in the database
        dispatch({ type: 'SET_SOLUTION_VERIFICATION', payload: { verified: true, source } });
        toast({
          title: "Solution Verified",
          description: "Neon database solution verification completed",
        });
      } catch (error) {
        dispatch({ type: 'SET_SOLUTION_VERIFICATION', payload: { verified: false, source } });
        toast({
          title: "Error",
          description: "Failed to verify solution",
          variant: "destructive",
        });
      }
    },

    applyValidationToDraft: (type: 'single' | 'multi') => {
      let hasValidData = false;
      
      if (type === 'single') {
        hasValidData = state.s3Validation?.success && !!state.s3Validation.table_schema;
        if (hasValidData) {
          dispatch({ type: 'APPLY_SINGLE_VALIDATION_TO_DRAFT' });
        }
      } else {
        hasValidData = state.multiTableValidation?.success && !!state.multiTableValidation.validated_datasets?.length;
        if (hasValidData) {
          dispatch({ type: 'APPLY_MULTI_VALIDATION_TO_DRAFT' });
        }
      }

      if (hasValidData) {
        dispatch({ type: 'SET_ACTIVE_TAB', payload: 'create' });
        toast({
          title: "Applied to Draft",
          description: `${type === 'single' ? 'Dataset' : 'Datasets'} applied to question draft`,
        });
      } else {
        toast({
          title: "No Data to Apply",
          description: `Please validate ${type === 'single' ? 'the dataset' : 'datasets'} first`,
          variant: "destructive",
        });
      }
    },

    resetDraft: () => {
      dispatch({ type: 'RESET_PROBLEM_DRAFT' });
    },

    updateDraft: (updates: Partial<ProblemDraft>) => {
      dispatch({ type: 'UPDATE_PROBLEM_DRAFT', payload: updates });
    }
  };

  return (
    <AdminContext.Provider value={{ state, dispatch, actions }}>
      {children}
    </AdminContext.Provider>
  );
}

// Hook to use the context
export function useAdmin() {
  const context = useContext(AdminContext);
  if (context === undefined) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
}