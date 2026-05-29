import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, ResponsiveContainer
} from 'recharts';

// Assume this is a placeholder for actual API calls
const mockApiData = {
  monthlyRevenue: [
    { month: 'Jan', revenue: 1200 },
    { month: 'Feb', revenue: 1500 },
    { month: 'Mar', revenue: 1300 },
    { month: 'Apr', revenue: 1600 },
    { month: 'May', revenue: 1800 },
    { month: 'Jun', revenue: 2000 }
  ],
  subscriptionCategories: [
    { name: 'Entertainment', count: 50 },
    { name: 'Utilities', count: 30 },
    { name: 'Software', count: 45 },
    { name: 'Education', count: 25 },
    { name: 'Health', count: 35 }
  ]
};

const fetchInsightsData = async () => {
  // In a real application, you would fetch from an API:
  // const response = await fetch('/api/v1/dashboard-stats');
  // const data = await response.json();
  // return data;

  // Using mock data for demonstration
  await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network delay
  return mockApiData;
};

const InsightsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchInsightsData();
        setData(result);
      } catch (err) {
        setError('Failed to load insights data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return <div>Loading insights...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="insights-container p-6">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Dashboard Insights</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Monthly Revenue Chart */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Monthly Revenue</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={data?.monthlyRevenue}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#8884d8" activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Subscription Categories Chart */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Subscription Categories</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={data?.subscriptionCategories}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default InsightsPage;
