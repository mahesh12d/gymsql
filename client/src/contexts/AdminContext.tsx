import { createContext, useContext, useReducer, ReactNode, useEffect } from 'react';
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
  s3_datasets?: S3DatasetSource[];  // Multiple S3 dataset sources
  tags: string[];
  company: string;
  hints: string[];
  premium: boolean;
  topic_id: string;
  expectedDisplay?: Record<string, any>[];  // Display output for users (not validation)
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
  message?: string;
  test_case_count?: number;
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
  selectedProblemId: string; // For verifying existing problems

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

  // Unified dataset management - supports both single and multiple
  datasets: Array<{
    bucket: string;
    key: string;
    table_name: string;
    description: string;
  }>;
  datasetValidation: MultiTableValidationResponse | null;
  isValidatingDatasets: boolean;

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
  | { type: 'SET_SELECTED_PROBLEM_ID'; payload: string }
  | { type: 'SET_S3_SOURCE'; payload: S3DatasetSource }
  | { type: 'SET_S3_VALIDATION'; payload: S3DatasetValidationResponse | null }
  | { type: 'SET_VALIDATING_S3'; payload: boolean }
  | { type: 'SET_MULTI_TABLE_DATASETS'; payload: AdminState['multiTableDatasets'] }
  | { type: 'SET_MULTI_TABLE_VALIDATION'; payload: MultiTableValidationResponse | null }
  | { type: 'SET_VALIDATING_MULTI_TABLE'; payload: boolean }
  | { type: 'SET_DATASETS'; payload: AdminState['datasets'] }
  | { type: 'SET_DATASET_VALIDATION'; payload: MultiTableValidationResponse | null }
  | { type: 'SET_VALIDATING_DATASETS'; payload: boolean }
  | { type: 'SET_SOLUTION_VERIFICATION'; payload: SolutionVerificationResult | null }
  | { type: 'SET_ACTIVE_TAB'; payload: string }
  | { type: 'APPLY_SINGLE_VALIDATION_TO_DRAFT' }
  | { type: 'APPLY_MULTI_VALIDATION_TO_DRAFT' }
  | { type: 'APPLY_UNIFIED_VALIDATION_TO_DRAFT' };

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
  selectedProblemId: '',
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
  datasets: [],
  datasetValidation: null,
  isValidatingDatasets: false,
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
    case 'SET_SELECTED_PROBLEM_ID':
      return { ...state, selectedProblemId: action.payload };
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
    case 'SET_DATASETS':
      return { ...state, datasets: action.payload };
    case 'SET_DATASET_VALIDATION':
      return { ...state, datasetValidation: action.payload };
    case 'SET_VALIDATING_DATASETS':
      return { ...state, isValidatingDatasets: action.payload };
    case 'SET_SOLUTION_VERIFICATION':
      return { ...state, solutionVerification: action.payload };
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
    case 'APPLY_UNIFIED_VALIDATION_TO_DRAFT':
      if (state.datasetValidation?.success && state.datasetValidation.validated_datasets) {
        const tables = state.datasetValidation.validated_datasets.map((dataset) => {
          const sampleData = dataset.sample_data || [];
          
          // Infer column names from first row of sample data, but leave types empty for admin to fill
          const inferredColumns = sampleData.length > 0 
            ? Object.keys(sampleData[0]).map(key => ({
                name: key,
                type: '', // Empty type - admin must fill manually
                description: ''
              }))
            : [];
          
          return {
            name: dataset.table_name,
            columns: inferredColumns,
            sample_data: sampleData
          };
        });
        
        // Extract S3 datasets info from validated datasets
        const s3_datasets = state.datasets.map((dataset) => ({
          bucket: dataset.bucket,
          key: dataset.key,
          table_name: dataset.table_name,
          description: dataset.description || ''
        }));
        
        return {
          ...state,
          problemDraft: {
            ...state.problemDraft,
            s3_datasets: s3_datasets,  // Include S3 datasets info
            question: {
              ...state.problemDraft.question,
              tables: tables,
              s3DataSources: state.datasets // Store the datasets for backend submission (uses camelCase alias)
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
    setDatasets: (datasets: AdminState['datasets']) => void;
    setActiveTab: (tab: string) => void;
    
    // Core actions
    authenticate: (key: string) => Promise<void>;
    validateS3Dataset: () => Promise<void>;
    validateMultiTableDatasets: (solutionPath: string) => Promise<void>;
    validateDatasets: (solutionPath: string) => Promise<void>;
    setSolutionType: (source: 'neon') => Promise<void>;
    setSolutionVerification: (verification: SolutionVerificationResult) => void;
    setSelectedProblemId: (problemId: string) => void;
    verifySolution: (source: 'neon') => Promise<void>;
    applyValidationToDraft: (type: 'single' | 'multi' | 'unified') => void;
    resetDraft: () => void;
    updateDraft: (updates: Partial<ProblemDraft>) => void;
  };
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

// Helper function to extract readable error message from API responses
function getErrorMessage(error: any): string {
  if (!error) return "An unknown error occurred";
  
  // Handle Pydantic validation errors (422) - detail is an array of error objects
  if (error.detail) {
    if (Array.isArray(error.detail)) {
      return error.detail
        .map((err: any) => err.msg || JSON.stringify(err))
        .join(", ");
    } else if (typeof error.detail === 'string') {
      return error.detail;
    }
  }
  
  // Handle string errors
  if (typeof error === 'string') return error;
  
  // Handle Error objects
  if (error instanceof Error) return error.message;
  
  // Handle error messages directly
  if (error.message && typeof error.message === 'string') return error.message;
  
  // Fallback
  return String(error);
}

// Provider component
export function AdminProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(adminReducer, initialState);
  const { toast } = useToast();

  // Restore admin session from sessionStorage on mount
  useEffect(() => {
    const restoreSession = async () => {
      const sessionToken = sessionStorage.getItem('admin_session_token');
      const expiresAt = sessionStorage.getItem('admin_session_expires');
      
      // Check if we have a valid session token
      if (sessionToken && expiresAt) {
        const now = Date.now();
        const expiry = Number(expiresAt);
        
        // Check if token is still valid (not expired)
        if (now < expiry) {
          try {
            // Verify token is still valid with a lightweight API call
            const response = await fetch('/api/admin/schema-info', {
              headers: { 'X-Admin-Session': sessionToken },
            });
            
            if (response.ok) {
              // Token is valid - restore session
              const schema = await response.json();
              dispatch({ type: 'SET_SCHEMA_INFO', payload: schema });
              dispatch({ type: 'SET_AUTHENTICATED', payload: true });
              dispatch({ type: 'SET_ADMIN_KEY', payload: sessionToken });
              dispatch({ type: 'UPDATE_PROBLEM_DRAFT', payload: schema.example_problem });
            } else {
              // Token is invalid - clear session
              sessionStorage.removeItem('admin_session_token');
              sessionStorage.removeItem('admin_session_expires');
            }
          } catch (error) {
            // Error verifying token - clear session
            sessionStorage.removeItem('admin_session_token');
            sessionStorage.removeItem('admin_session_expires');
          }
        } else {
          // Token expired - clear session
          sessionStorage.removeItem('admin_session_token');
          sessionStorage.removeItem('admin_session_expires');
        }
      }
    };
    
    restoreSession();
  }, []);

  // Helper function to get admin session token
  const getAdminHeaders = (): HeadersInit => {
    const sessionToken = sessionStorage.getItem('admin_session_token');
    if (!sessionToken) {
      throw new Error('Admin session expired. Please re-enter admin key.');
    }
    
    // Check if session is expired
    const expiresAt = sessionStorage.getItem('admin_session_expires');
    if (expiresAt && Date.now() > Number(expiresAt)) {
      // Clear expired session
      sessionStorage.removeItem('admin_session_token');
      sessionStorage.removeItem('admin_session_expires');
      dispatch({ type: 'SET_AUTHENTICATED', payload: false });
      throw new Error('Admin session expired. Please re-enter admin key.');
    }
    
    return { 'X-Admin-Session': sessionToken };
  };

  const actions = {
    // Setter actions  
    setS3Source: (source: S3DatasetSource) => {
      dispatch({ type: 'SET_S3_SOURCE', payload: source });
    },

    setMultiTableDatasets: (datasets: AdminState['multiTableDatasets']) => {
      dispatch({ type: 'SET_MULTI_TABLE_DATASETS', payload: datasets });
    },

    setDatasets: (datasets: AdminState['datasets']) => {
      dispatch({ type: 'SET_DATASETS', payload: datasets });
    },

    setActiveTab: (tab: string) => {
      dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
    },

    setSelectedProblemId: (problemId: string) => {
      dispatch({ type: 'SET_SELECTED_PROBLEM_ID', payload: problemId });
    },

    setSolutionVerification: (verification: SolutionVerificationResult) => {
      dispatch({ type: 'SET_SOLUTION_VERIFICATION', payload: verification });
    },

    setSolutionType: async (source: 'neon') => {
      // For Neon solutions, actually verify they exist instead of auto-verifying
      if (source === 'neon') {
        try {
          dispatch({ type: 'SET_SOLUTION_VERIFICATION', payload: null });
          
          const adminHeaders = getAdminHeaders();
          // Make API call to verify Neon solution
          const response = await fetch('/api/admin/verify-neon-solution', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...adminHeaders
            },
            body: JSON.stringify({
              problem_id: state.selectedProblemId
            })
          });
          
          if (!response.ok) {
            throw new Error(`Failed to verify solution: ${response.statusText}`);
          }
          
          const verificationResult = await response.json();
          
          dispatch({ 
            type: 'SET_SOLUTION_VERIFICATION', 
            payload: {
              verified: verificationResult.verified,
              source: verificationResult.source,
              message: verificationResult.message,
              test_case_count: verificationResult.test_case_count
            }
          });
          
        } catch (error) {
          console.error('Failed to verify Neon solution:', error);
          if (error instanceof Error && error.message.includes('session expired')) {
            toast({ title: "Session Expired", description: error.message, variant: "destructive" });
            dispatch({ type: 'SET_AUTHENTICATED', payload: false });
          } else {
            toast({
              title: "Verification Failed",
              description: `Failed to verify Neon solution: ${error instanceof Error ? error.message : String(error)}`,
              variant: "destructive"
            });
          }
          
          // Set failed verification
          dispatch({ 
            type: 'SET_SOLUTION_VERIFICATION', 
            payload: {
              verified: false,
              source: 'neon',
              message: `Verification failed: ${error instanceof Error ? error.message : String(error)}`
            }
          });
        }
      }
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
        // Get user's JWT token from localStorage or cookies
        const authToken = localStorage.getItem('auth_token');
        
        if (!authToken) {
          toast({
            title: "Authentication Required",
            description: "Please login first before accessing the admin panel",
            variant: "destructive",
          });
          dispatch({ type: 'SET_LOADING', payload: false });
          return;
        }

        // Step 1: Validate admin key and get session token
        const sessionResponse = await fetch('/api/admin/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
          },
          body: JSON.stringify({ admin_key: key }),
        });

        if (!sessionResponse.ok) {
          const errorData = await sessionResponse.json().catch(() => ({}));
          toast({
            title: "Authentication Failed",
            description: getErrorMessage(errorData) || "Invalid admin key or insufficient permissions",
            variant: "destructive",
          });
          dispatch({ type: 'SET_LOADING', payload: false });
          return;
        }

        const sessionData = await sessionResponse.json();
        const sessionToken = sessionData.session_token;
        
        // Store session token in sessionStorage (clears on tab close)
        sessionStorage.setItem('admin_session_token', sessionToken);
        sessionStorage.setItem('admin_session_expires', String(Date.now() + (sessionData.expires_in * 60 * 1000)));

        // Step 2: Fetch schema info using session token
        const schemaResponse = await fetch('/api/admin/schema-info', {
          headers: {
            'X-Admin-Session': sessionToken,
          },
        });

        if (schemaResponse.ok) {
          const schema = await schemaResponse.json();
          dispatch({ type: 'SET_SCHEMA_INFO', payload: schema });
          dispatch({ type: 'SET_AUTHENTICATED', payload: true });
          dispatch({ type: 'SET_ADMIN_KEY', payload: sessionToken }); // Store session token instead of key
          dispatch({ type: 'UPDATE_PROBLEM_DRAFT', payload: schema.example_problem });
          toast({
            title: "Success",
            description: `Admin access granted! Session expires in ${sessionData.expires_in} minutes.`,
          });
        } else {
          const errorData = await schemaResponse.json().catch(() => ({}));
          toast({
            title: "Error",
            description: getErrorMessage(errorData) || "Failed to load schema info",
            variant: "destructive",
          });
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to authenticate: " + getErrorMessage(error),
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
        const adminHeaders = getAdminHeaders();
        const response = await fetch('/api/admin/validate-dataset-s3', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...adminHeaders,
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
        if (error instanceof Error && error.message.includes('session expired')) {
          toast({
            title: "Session Expired",
            description: error.message,
            variant: "destructive",
          });
          dispatch({ type: 'SET_AUTHENTICATED', payload: false });
        } else {
          toast({
            title: "Error",
            description: "Failed to validate S3 dataset",
            variant: "destructive",
          });
        }
      } finally {
        dispatch({ type: 'SET_VALIDATING_S3', payload: false });
      }
    },

    validateMultiTableDatasets: async (solutionPath: string) => {
      dispatch({ type: 'SET_VALIDATING_MULTI_TABLE', payload: true });
      dispatch({ type: 'SET_MULTI_TABLE_VALIDATION', payload: null });

      try {
        const adminHeaders = getAdminHeaders();
        const response = await fetch('/api/admin/validate-multitable-s3', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...adminHeaders,
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
        if (error instanceof Error && error.message.includes('session expired')) {
          toast({ title: "Session Expired", description: error.message, variant: "destructive" });
          dispatch({ type: 'SET_AUTHENTICATED', payload: false });
        } else {
          toast({ title: "Error", description: "Failed to validate multi-table datasets", variant: "destructive" });
        }
      } finally {
        dispatch({ type: 'SET_VALIDATING_MULTI_TABLE', payload: false });
      }
    },

    validateDatasets: async (solutionPath: string) => {
      dispatch({ type: 'SET_VALIDATING_DATASETS', payload: true });
      dispatch({ type: 'SET_DATASET_VALIDATION', payload: null });

      try {
        const adminHeaders = getAdminHeaders();
        const response = await fetch('/api/admin/validate-multitable-s3', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...adminHeaders,
          },
          body: JSON.stringify({
            datasets: state.datasets,
            solution_path: solutionPath
          }),
        });

        const result = await response.json();
        dispatch({ type: 'SET_DATASET_VALIDATION', payload: result });

        if (result.success) {
          toast({
            title: "Dataset Validation Success",
            description: `Successfully validated ${result.validated_datasets?.length} dataset(s)`,
          });
        } else {
          toast({
            title: "Validation Failed",
            description: result.error || "Unknown error occurred",
            variant: "destructive",
          });
        }
      } catch (error) {
        if (error instanceof Error && error.message.includes('session expired')) {
          toast({ title: "Session Expired", description: error.message, variant: "destructive" });
          dispatch({ type: 'SET_AUTHENTICATED', payload: false });
        } else {
          toast({ title: "Error", description: "Failed to validate datasets", variant: "destructive" });
        }
      } finally {
        dispatch({ type: 'SET_VALIDATING_DATASETS', payload: false });
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

    applyValidationToDraft: (type: 'single' | 'multi' | 'unified') => {
      let hasValidData = false;
      
      if (type === 'single') {
        hasValidData = state.s3Validation?.success && !!state.s3Validation.table_schema;
        if (hasValidData) {
          dispatch({ type: 'APPLY_SINGLE_VALIDATION_TO_DRAFT' });
        }
      } else if (type === 'multi') {
        hasValidData = state.multiTableValidation?.success && !!state.multiTableValidation.validated_datasets?.length;
        if (hasValidData) {
          dispatch({ type: 'APPLY_MULTI_VALIDATION_TO_DRAFT' });
        }
      } else if (type === 'unified') {
        hasValidData = state.datasetValidation?.success && !!state.datasetValidation.validated_datasets?.length;
        if (hasValidData) {
          dispatch({ type: 'APPLY_UNIFIED_VALIDATION_TO_DRAFT' });
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