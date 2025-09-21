import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Shield } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { AdminProvider, useAdmin } from '@/contexts/AdminContext';
import { CreateQuestionTab } from '@/components/admin/CreateQuestionTab';
import { DataSourceTab } from '@/components/admin/DataSourceTab';
import { SolutionsTab } from '@/components/admin/SolutionsTab';
import { SchemaInfoTab } from '@/components/admin/SchemaInfoTab';

function AdminPanelContent() {
  const { state, actions } = useAdmin();
  const [adminKey, setAdminKey] = useState('');

  const handleAuthenticate = () => {
    actions.authenticate(adminKey);
  };

  if (!state.isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <Shield className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl text-center">Admin Panel</CardTitle>
            <p className="text-center text-muted-foreground">
              Enter your admin key to access the management interface
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="admin-key">Admin Key</Label>
              <Input
                id="admin-key"
                type="password"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAuthenticate()}
                placeholder="Enter admin key"
                data-testid="input-admin-key"
              />
            </div>
            <Button 
              className="w-full" 
              onClick={handleAuthenticate}
              disabled={state.loading}
              data-testid="button-authenticate"
            >
              {state.loading ? 'Authenticating...' : 'Access Admin Panel'}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Admin Panel</h1>
              <p className="text-muted-foreground">
                Manage problems, data sources, solutions, and schema information
              </p>
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Shield className="h-4 w-4" />
              <span>Authenticated</span>
            </div>
          </div>
        </div>

        <Tabs 
          value={state.activeTab} 
          onValueChange={actions.setActiveTab} 
          className="space-y-6"
        >
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="create" data-testid="tab-create-question">
              Create Question
            </TabsTrigger>
            <TabsTrigger value="datasource" data-testid="tab-data-source">
              Data Source
            </TabsTrigger>
            <TabsTrigger value="solutions" data-testid="tab-solutions">
              Solutions
            </TabsTrigger>
            <TabsTrigger value="schema" data-testid="tab-schema-info">
              Schema Info
            </TabsTrigger>
          </TabsList>

          <TabsContent value="create" className="space-y-6">
            <CreateQuestionTab />
          </TabsContent>

          <TabsContent value="datasource" className="space-y-6">
            <DataSourceTab />
          </TabsContent>

          <TabsContent value="solutions" className="space-y-6">
            <SolutionsTab />
          </TabsContent>

          <TabsContent value="schema" className="space-y-6">
            <SchemaInfoTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default function AdminPanel() {
  return (
    <AdminProvider>
      <AdminPanelContent />
    </AdminProvider>
  );
}