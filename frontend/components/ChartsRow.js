import { Icon } from "../lib/icons";
import { ratchetTimeline, resolutionPathCounts } from "../lib/chartData";
import RatchetTimelineChart from "./charts/RatchetTimelineChart";
import ResolutionPathChart from "./charts/ResolutionPathChart";

export default function ChartsRow({ feed }) {
  const timeline = ratchetTimeline(feed);
  const counts = resolutionPathCounts(feed);

  return (
    <div className="grid charts-row">
      <div className="panel">
        <div className="panel-head">
          <div className="panel-title">
            <Icon.Activity />
            <h2>Ratchet Effect Over Time</h2>
          </div>
          <span className="panel-note">cumulative fabric hit rate</span>
        </div>
        <RatchetTimelineChart data={timeline} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div className="panel-title">
            <Icon.Database />
            <h2>Resolution Path</h2>
          </div>
          <span className="panel-note">how each incident was actually resolved</span>
        </div>
        <ResolutionPathChart counts={counts} />
      </div>
    </div>
  );
}
