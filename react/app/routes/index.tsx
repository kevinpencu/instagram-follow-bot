import { useState, useEffect } from "react";
import type { Route } from "./+types/index";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Checkbox } from "~/components/ui/checkbox";
import { Badge } from "~/components/ui/badge";
import { Play, PlayCircle, Settings, Loader2 } from "lucide-react";
import { apiService, type Profile, type ProfileStatus } from "~/lib/api";
import { WorkerInputModal } from "~/components/worker-input-modal";

export function meta({ }: Route.MetaArgs) {
  return [
    { title: "Instagram Follow Bot" },
    { name: "description", content: "Run Follow Operations. Powered by AirTable, AdsPower & Selenium." },
  ];
}

type ProfileData = Profile & {
  status?: ProfileStatus;
};

export default function Index() {
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [profiles, setProfiles] = useState<ProfileData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStartingAll, setIsStartingAll] = useState(false);
  const [isStartingSelected, setIsStartingSelected] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalAction, setModalAction] = useState<"start-all" | "start-selected">("start-all");

  const fetchProfiles = async () => {
    try {
      const profilesData = await apiService.getProfiles();
      setProfiles(profilesData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const statusData = await apiService.getStatus();
      
      setProfiles(currentProfiles => {
        return currentProfiles.map(profile => {
          const status = statusData.activeProfiles[profile.ads_power_id];
          const isScheduled = statusData.scheduled.includes(profile.ads_power_id);
          
          if (status) {
            return { ...profile, status };
          } else if (isScheduled) {
            return {
              ...profile,
              status: {
                ads_power_id: profile.ads_power_id,
                username: profile.username,
                bot_status: 'scheduled' as const,
                total_accounts: 0,
                total_followed: 0,
                total_follow_failed: 0,
                total_already_followed: 0,
              }
            };
          } else {
            return { ...profile, status: undefined };
          }
        });
      });
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  };

  useEffect(() => {
    const initializeData = async () => {
      await fetchProfiles();
      await fetchStatus();
    };
    
    initializeData();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedRows(new Set(profiles.map(row => row.ads_power_id)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (rowId: string, checked: boolean) => {
    const newSelected = new Set(selectedRows);
    if (checked) {
      newSelected.add(rowId);
    } else {
      newSelected.delete(rowId);
    }
    setSelectedRows(newSelected);
  };

  const handleStartAll = () => {
    setModalAction("start-all");
    setModalOpen(true);
  };

  const handleStartSelected = () => {
    setModalAction("start-selected");
    setModalOpen(true);
  };

  const handleConfirmAction = async (maxWorkers: number) => {
    try {
      if (modalAction === "start-all") {
        setIsStartingAll(true);
        await apiService.startAll(maxWorkers);
      } else {
        setIsStartingSelected(true);
        const selectedAdsPowerIds = Array.from(selectedRows);
        await apiService.startSelected(selectedAdsPowerIds, maxWorkers);
      }
      fetchStatus();
      setModalOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${modalAction.replace('-', ' ')}`);
    } finally {
      setIsStartingAll(false);
      setIsStartingSelected(false);
    }
  };


  const isAllSelected = selectedRows.size === profiles.length && profiles.length > 0;
  const isIndeterminate = selectedRows.size > 0 && selectedRows.size < profiles.length;

  const getStatusBadge = (status?: ProfileStatus) => {
    if (!status) return null;
    
    const statusConfig = {
      scheduled: { variant: 'secondary' as const, label: 'Scheduled', animate: true },
      running: { variant: 'default' as const, label: 'Running', animate: true },
      done: { variant: 'outline' as const, label: 'Done', animate: false },
      failed: { variant: 'destructive' as const, label: 'Failed', animate: false },
      seleniumFailed: { variant: 'destructive' as const, label: 'Selenium Failed', animate: false },
      adsPowerFailed: { variant: 'destructive' as const, label: 'AdsPower Failed', animate: false },
      followblocked: { variant: 'destructive' as const, label: 'Follow Blocked', animate: false },
      accountLoggedOut: { variant: 'destructive' as const, label: 'Account Logged Out', animate: false },
      accountSuspended: { variant: 'destructive' as const, label: 'Account Suspended', animate: false },
      banned: { variant: 'destructive' as const, label: 'Banned', animate: false },
      notargets: { variant: 'secondary' as const, label: 'No Targets', animate: false },
    };
    
    const config = statusConfig[status.bot_status];
    const animationClass = config.animate ? 'animate-pulse' : '';
    
    return (
      <Badge 
        variant={config.variant} 
        className={`${animationClass} transition-all duration-300`}
      >
        {config.label}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Instagram Follow Bot</h1>
          <p className="text-muted-foreground text-sm sm:text-base">Start automated follow operations</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <Button 
            onClick={handleStartSelected} 
            disabled={selectedRows.size === 0 || isStartingSelected || isLoading} 
            className="gap-2 w-full sm:w-auto"
          >
            {isStartingSelected ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            <span className="hidden xs:inline">Start Selected</span>
            <span className="xs:hidden">Selected</span> ({selectedRows.size})
          </Button>
          <Button 
            onClick={handleStartAll} 
            variant="outline" 
            disabled={isStartingAll || isLoading}
            className="gap-2 w-full sm:w-auto"
          >
            {isStartingAll ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
            Start All
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="text-sm text-destructive">
              Error: {error}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg sm:text-xl">Fetched Profiles from API (AirTable)</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={isAllSelected}
                      onCheckedChange={handleSelectAll}
                      aria-label="Select all"
                      {...(isIndeterminate && { 'data-state': 'indeterminate' })}
                    />
                  </TableHead>
                  <TableHead className="min-w-[120px]">Username</TableHead>
                  <TableHead className="min-w-[100px] hidden sm:table-cell">AdsPower ID</TableHead>
                  <TableHead className="min-w-[80px] hidden md:table-cell">Status</TableHead>
                  <TableHead className="min-w-[60px] hidden lg:table-cell">Total</TableHead>
                  <TableHead className="min-w-[60px] hidden lg:table-cell">Followed</TableHead>
                  <TableHead className="min-w-[60px] hidden lg:table-cell">Already</TableHead>
                  <TableHead className="min-w-[60px] hidden lg:table-cell">Failed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading profiles...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : profiles.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      No profiles found
                    </TableCell>
                  </TableRow>
                ) : (
                  profiles.map((profile, index) => (
                    <TableRow key={profile.ads_power_id} className={selectedRows.has(profile.ads_power_id) ? 'bg-muted/50' : ''}>
                      <TableCell className="text-center text-sm text-muted-foreground">
                        {index + 1}
                      </TableCell>
                      <TableCell>
                        <Checkbox
                          checked={selectedRows.has(profile.ads_power_id)}
                          onCheckedChange={(checked) => handleSelectRow(profile.ads_power_id, checked as boolean)}
                          aria-label={`Select ${profile.username}`}
                        />
                      </TableCell>
                      <TableCell className="font-medium">
                        <div className="flex flex-col gap-1">
                          <span className="font-semibold">{profile.username}</span>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground sm:hidden">
                            <Settings className="h-3 w-3" />
                            <span>{profile.ads_power_id}</span>
                            {profile.status && (
                              <div className="md:hidden">
                                {getStatusBadge(profile.status)}
                              </div>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground hidden sm:table-cell">
                        <div className="flex items-center gap-2">
                          <Settings className="h-4 w-4 text-muted-foreground/60" />
                          <span className="font-mono text-sm">{profile.ads_power_id}</span>
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        {getStatusBadge(profile.status)}
                      </TableCell>
                      <TableCell className="text-center hidden lg:table-cell">
                        {profile.status?.total_accounts ?? '-'}
                      </TableCell>
                      <TableCell className="text-center hidden lg:table-cell">
                        {profile.status?.total_followed ?? '-'}
                      </TableCell>
                      <TableCell className="text-center hidden lg:table-cell">
                        {profile.status?.total_already_followed ?? '-'}
                      </TableCell>
                      <TableCell className="text-center hidden lg:table-cell">
                        {profile.status?.total_follow_failed ?? '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <WorkerInputModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={handleConfirmAction}
        actionType={modalAction}
        selectedCount={selectedRows.size}
        isLoading={isStartingAll || isStartingSelected}
      />
    </div>
  );
}
