console.log('Dashboard data:', dashboardData);

function Card({ title, value, subtitle }) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-xl font-semibold mb-2">{title}</h3>
            <p className="text-3xl font-bold text-blue-600">{value}</p>
            {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
    );
}

function Chart({ id, type, data, options }) {
    React.useEffect(() => {
        const ctx = document.getElementById(id).getContext('2d');
        new Chart(ctx, { type, data, options });
    }, []);

    return <canvas id={id}></canvas>;
}

function Dashboard({ data }) {
    console.log('Rendering Dashboard with data:', data);

    const sessionsPerMonthData = {
        labels: data.sessions_per_month?.map(item => item.month) || [],
        datasets: [{
            label: 'Training Sessions',
            data: data.sessions_per_month?.map(item => item.count) || [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    };

    const topRequestedTrainingsData = {
        labels: data.top_requested_trainings?.map(item => item.training_programme__title) || [],
        datasets: [{
            label: 'Requests',
            data: data.top_requested_trainings?.map(item => item.count) || [],
            backgroundColor: 'rgba(75, 192, 192, 0.6)',
        }]
    };

    const departmentParticipationData = {
        labels: data.department_participation?.map(item => item.name) || [],
        datasets: [{
            label: 'Participants',
            data: data.department_participation?.map(item => item.participant_count) || [],
            backgroundColor: 'rgba(153, 102, 255, 0.6)',
        }]
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-8">Enhanced Training Management Dashboard</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card title="Training Sessions" value={data.counts?.training_sessions || 0} />
                <Card title="Request Trainings" value={data.counts?.request_trainings || 0} />
                <Card title="Superior Assigned Trainings" value={data.counts?.superior_assigned_trainings || 0} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-xl font-semibold mb-4">Training Sessions per Month</h3>
                    <Chart id="sessionsPerMonthChart" type="line" data={sessionsPerMonthData} options={{responsive: true}} />
                </div>
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-xl font-semibold mb-4">Top Requested Trainings</h3>
                    <Chart id="topRequestedTrainingsChart" type="bar" data={topRequestedTrainingsData} options={{responsive: true, indexAxis: 'y'}} />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-xl font-semibold mb-4">Department Participation</h3>
                    <Chart id="departmentParticipationChart" type="bar" data={departmentParticipationData} options={{responsive: true}} />
                </div>
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-xl font-semibold mb-4">Training Effectiveness</h3>
                    <Card 
                        title="Average Feedback Score" 
                        value={(data.avg_feedback_score != null ? data.avg_feedback_score.toFixed(2) : 'N/A')} 
                        subtitle="Out of 5" 
                    />
                    <h4 className="text-lg font-semibold mt-4 mb-2">Top Trainers</h4>
                    <ul className="list-disc list-inside">
                        {(data.trainer_effectiveness || []).map((trainer, index) => (
                            <li key={index}>
                                {trainer.training_session__trainer__name} - {trainer.avg_score != null ? trainer.avg_score.toFixed(2) : 'N/A'}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-2xl font-semibold mb-4">Recent Training Sessions</h2>
                    <div className="overflow-x-auto">
                        <table className="min-w-full">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="px-4 py-2 text-left">ID</th>
                                    <th className="px-4 py-2 text-left">Title</th>
                                    <th className="px-4 py-2 text-left">Date</th>
                                    <th className="px-4 py-2 text-left">Venue</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data.recent_training_sessions || []).map(session => (
                                    <tr key={session.id} className="border-b">
                                        <td className="px-4 py-2">{session.id}</td>
                                        <td className="px-4 py-2">{session.training_programme__title}</td>
                                        <td className="px-4 py-2">{session.date}</td>
                                        <td className="px-4 py-2">{session.venue__name}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-2xl font-semibold mb-4">Recent Request Trainings</h2>
                    <div className="overflow-x-auto">
                        <table className="min-w-full">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="px-4 py-2 text-left">ID</th>
                                    <th className="px-4 py-2 text-left">User</th>
                                    <th className="px-4 py-2 text-left">Training</th>
                                    <th className="px-4 py-2 text-left">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data.recent_request_trainings || []).map(request => (
                                    <tr key={request.id} className="border-b">
                                        <td className="px-4 py-2">{request.id}</td>
                                        <td className="px-4 py-2">{request.custom_user__username}</td>
                                        <td className="px-4 py-2">{request.training_programme__title}</td>
                                        <td className="px-4 py-2">{request.status__name}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

ReactDOM.render(
    <Dashboard data={dashboardData} />,
    document.getElementById('dashboard-root')
);