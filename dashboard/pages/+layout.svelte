<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout
	{data}
	title="Monitor IC Chile"
	homePageName="Resumen"
	builtWithEvidence={false}
	githubRepo="https://github.com/JosueIgnacio/monitor-ic-chile"
	hideBreadcrumbs={true}
>
	<slot slot="content" />
</EvidenceDefaultLayout>
