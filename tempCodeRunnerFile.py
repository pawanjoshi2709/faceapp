def plot_charts(logs, selected_date=None, selected_month=None, selected_year=None, start_year=None, end_year=None):
    df = pd.DataFrame(logs, columns=['date', 'start_time'])
    df['date'] = pd.to_datetime(df['date'])
    
    # Ensure 'start_time' is a string and handle missing values
    df['start_time'] = df['start_time'].astype(str).fillna('00:00:00')

    # Extract hour from 'start_time'
    df['hour'] = df['start_time'].apply(lambda x: int(x.split(':')[0]) if ':' in x else 0)
    df['day'] = df['date'].dt.day
    df['month'] = df['date'].dt.strftime('%b')
    df['year'] = df['date'].dt.year

    # Hour chart
    if selected_date:
        selected_date = pd.to_datetime(selected_date)
        df = df[df['date'].dt.date == selected_date.date()]
    hour_counts = df.groupby('hour').size().reindex(range(24), fill_value=0).reset_index(name='count')
    hour_count_fig = px.bar(hour_counts, x='hour', y='count', title='Log Counts by Hour', labels={'hour': 'Hour', 'count': 'Log Count'})
    hour_chart_html = pio.to_html(hour_count_fig, full_html=False)

    # Day chart
    if selected_month:
        latest_month = datetime.strptime(selected_month, '%Y-%m').month
        days_in_month = pd.Period(year=df['date'].max().year, month=latest_month, freq='M').days_in_month
        day_counts = df[df['date'].dt.month == latest_month].groupby('day').size().reindex(range(1, days_in_month + 1), fill_value=0).reset_index(name='count')
    else:
        day_counts = df.groupby('day').size().reindex(range(1, 32), fill_value=0).reset_index(name='count')
    day_count_fig = px.bar(day_counts, x='day', y='count', title='Log Counts by Day', labels={'day': 'Day', 'count': 'Log Count'})
    day_chart_html = pio.to_html(day_count_fig, full_html=False)

    # Month chart
    if selected_year:
        month_counts = df[df['date'].dt.year == int(selected_year)].groupby('month').size().reindex(pd.date_range(start=f'{selected_year}-01-01', end=f'{selected_year}-12-01', freq='M').strftime('%b'), fill_value=0).reset_index(name='count')
    else:
        month_counts = df.groupby('month').size().reindex(pd.date_range(start='2000-01-01', end='2024-12-01', freq='M').strftime('%b'), fill_value=0).reset_index(name='count')
    month_counts.rename(columns={'index': 'month'}, inplace=True)
    month_count_fig = px.bar(month_counts, x='month', y='count', title='Log Counts by Month', labels={'month': 'Month', 'count': 'Log Count'})
    month_chart_html = pio.to_html(month_count_fig, full_html=False)

    # Year chart
    if start_year and end_year:
        year_counts = df[df['date'].dt.year.between(int(start_year), int(end_year))].groupby('year').size().reindex(range(int(start_year), int(end_year) + 1), fill_value=0).reset_index(name='count')
    else:
        year_counts = df.groupby('year').size().reindex(range(df['date'].dt.year.min(), df['date'].dt.year.max() + 1), fill_value=0).reset_index(name='count')
    year_count_fig = px.bar(year_counts, x='year', y='count', title='Log Counts by Year', labels={'year': 'Year', 'count': 'Log Count'})
    year_chart_html = pio.to_html(year_count_fig, full_html=False)

    return hour_chart_html, day_chart_html, month_chart_html, year_chart_html

@app.route('/analyze/<int:face_id>', methods=['GET'])
def analyze_face(face_id):
    logs = fetch_recognition_logs(face_id)
    if logs:
        hour_chart_html, day_chart_html, month_chart_html, year_chart_html = plot_charts(logs)
        return render_template('face_modal.html', face_id=face_id, hour_chart_html=hour_chart_html, day_chart_html=day_chart_html, month_chart_html=month_chart_html, year_chart_html=year_chart_html)
    else:
        flash('No recognition logs found for the selected face.', 'warning')
        return redirect(url_for('analyze'))