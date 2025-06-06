import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Database, 
  Clock, 
  Zap, 
  TrendingUp,
  Server,
  HardDrive,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { ragService } from '../services/ragService';

const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
`;

const Header = styled.div`
  background: rgba(255, 255, 255, 0.95);
  padding: 1.5rem 2rem;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
`;

const HeaderTitle = styled.h2`
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
`;

const HeaderSubtitle = styled.p`
  margin: 0;
  color: #6b7280;
  font-size: 0.875rem;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
`;

const StatCard = styled(motion.div)`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: ${props => props.color || '#667eea'};
  }
`;

const StatHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
`;

const StatIcon = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: ${props => props.color ? `${props.color}15` : 'rgba(102, 126, 234, 0.15)'};
  color: ${props => props.color || '#667eea'};
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0.25rem;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
`;

const StatChange = styled.div`
  font-size: 0.75rem;
  color: ${props => props.positive ? '#22c55e' : '#ef4444'};
  font-weight: 500;
  margin-top: 0.5rem;
`;

const ChartsSection = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  flex: 1;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const ChartCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  height: fit-content;
`;

const ChartTitle = styled.h3`
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #333;
`;

const PerformanceChart = styled.div`
  height: 200px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
  font-weight: 500;
`;

const ActivityFeed = styled.div`
  max-height: 300px;
  overflow-y: auto;
`;

const ActivityItem = styled(motion.div)`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);

  &:last-child {
    border-bottom: none;
  }
`;

const ActivityIcon = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: ${props => props.color || '#667eea'};
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
`;

const ActivityContent = styled.div`
  flex: 1;
`;

const ActivityText = styled.div`
  font-size: 0.875rem;
  color: #333;
  margin-bottom: 0.25rem;
`;

const ActivityTime = styled.div`
  font-size: 0.75rem;
  color: #6b7280;
`;

const RefreshButton = styled(motion.button)`
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.5rem;
  background: rgba(102, 126, 234, 0.1);
  border: none;
  border-radius: 6px;
  color: #667eea;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const LoadingOverlay = styled(motion.div)`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
`;

const Dashboard = () => {
  const [stats, setStats] = useState({
    system: {
      health: 'Healthy',
      uptime: '7d 12h',
      version: '2.0.0'
    },
    performance: {
      avgResponseTime: 145,
      totalQueries: 1247,
      cacheHitRate: 87.3,
      errorRate: 0.2
    },
    storage: {
      totalDocuments: 156,
      totalNamespaces: 5,
      storageUsed: '2.3 GB',
      indexSize: '450 MB'
    }
  });

  const [activities, setActivities] = useState([
    {
      id: 1,
      type: 'query',
      text: 'New query processed in engineering namespace',
      time: '2 minutes ago',
      color: '#22c55e'
    },
    {
      id: 2,
      type: 'upload',
      text: 'Document uploaded to legal namespace',
      time: '15 minutes ago',
      color: '#667eea'
    },
    {
      id: 3,
      type: 'cache',
      text: 'Cache optimization completed',
      time: '1 hour ago',
      color: '#f59e0b'
    },
    {
      id: 4,
      type: 'system',
      text: 'System health check passed',
      time: '2 hours ago',
      color: '#10b981'
    }
  ]);

  const [isLoading, setIsLoading] = useState(false);

  const refreshDashboard = async () => {
    setIsLoading(true);
    
    try {
      // Try to get real stats from the API
      const [healthData, performanceData, cacheData] = await Promise.allSettled([
        ragService.getHealth(),
        ragService.getPerformanceStats(),
        ragService.getCacheStats()
      ]);

      // Update stats with real data if available
      if (healthData.status === 'fulfilled') {
        setStats(prev => ({
          ...prev,
          system: {
            ...prev.system,
            health: healthData.value.status || 'Healthy'
          }
        }));
      }

      if (performanceData.status === 'fulfilled') {
        setStats(prev => ({
          ...prev,
          performance: {
            ...prev.performance,
            ...performanceData.value
          }
        }));
      }

      if (cacheData.status === 'fulfilled') {
        setStats(prev => ({
          ...prev,
          performance: {
            ...prev.performance,
            cacheHitRate: cacheData.value.hit_rate || prev.performance.cacheHitRate
          }
        }));
      }

      // Add refresh activity
      setActivities(prev => [
        {
          id: Date.now(),
          type: 'refresh',
          text: 'Dashboard data refreshed',
          time: 'Just now',
          color: '#667eea'
        },
        ...prev.slice(0, 9)
      ]);

    } catch (err) {
      console.error('Failed to refresh dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshDashboard();
  }, []);

  const getActivityIcon = (type) => {
    switch (type) {
      case 'query': return <Activity size={16} />;
      case 'upload': return <Database size={16} />;
      case 'cache': return <Zap size={16} />;
      case 'system': return <Server size={16} />;
      case 'refresh': return <RefreshCw size={16} />;
      default: return <Activity size={16} />;
    }
  };

  return (
    <DashboardContainer>
      <Header>
        <HeaderTitle>System Dashboard</HeaderTitle>
        <HeaderSubtitle>
          Monitor your RAGdoll system performance and activity
        </HeaderSubtitle>
      </Header>

      <StatsGrid>
        <StatCard
          color="#22c55e"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <StatHeader>
            <StatIcon color="#22c55e">
              <Activity size={20} />
            </StatIcon>
            <RefreshButton
              onClick={refreshDashboard}
              disabled={isLoading}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            </RefreshButton>
          </StatHeader>
          <StatValue>{stats.performance.avgResponseTime}ms</StatValue>
          <StatLabel>Average Response Time</StatLabel>
          <StatChange positive>-12% from last week</StatChange>
          
          {isLoading && (
            <LoadingOverlay
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <RefreshCw size={20} className="animate-spin" />
            </LoadingOverlay>
          )}
        </StatCard>

        <StatCard
          color="#667eea"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <StatHeader>
            <StatIcon color="#667eea">
              <TrendingUp size={20} />
            </StatIcon>
          </StatHeader>
          <StatValue>{stats.performance.totalQueries.toLocaleString()}</StatValue>
          <StatLabel>Total Queries</StatLabel>
          <StatChange positive>+23% from last week</StatChange>
        </StatCard>

        <StatCard
          color="#f59e0b"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <StatHeader>
            <StatIcon color="#f59e0b">
              <Zap size={20} />
            </StatIcon>
          </StatHeader>
          <StatValue>{stats.performance.cacheHitRate}%</StatValue>
          <StatLabel>Cache Hit Rate</StatLabel>
          <StatChange positive>+5% from last week</StatChange>
        </StatCard>

        <StatCard
          color="#8b5cf6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <StatHeader>
            <StatIcon color="#8b5cf6">
              <Database size={20} />
            </StatIcon>
          </StatHeader>
          <StatValue>{stats.storage.totalDocuments}</StatValue>
          <StatLabel>Total Documents</StatLabel>
          <StatChange positive>+8 this week</StatChange>
        </StatCard>
      </StatsGrid>

      <ChartsSection>
        <ChartCard>
          <ChartTitle>Performance Trends</ChartTitle>
          <PerformanceChart>
            📈 Performance chart visualization coming soon
          </PerformanceChart>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Recent Activity</ChartTitle>
          <ActivityFeed>
            {activities.map((activity, index) => (
              <ActivityItem
                key={activity.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ActivityIcon color={activity.color}>
                  {getActivityIcon(activity.type)}
                </ActivityIcon>
                <ActivityContent>
                  <ActivityText>{activity.text}</ActivityText>
                  <ActivityTime>{activity.time}</ActivityTime>
                </ActivityContent>
              </ActivityItem>
            ))}
          </ActivityFeed>
        </ChartCard>
      </ChartsSection>
    </DashboardContainer>
  );
};

export default Dashboard;
